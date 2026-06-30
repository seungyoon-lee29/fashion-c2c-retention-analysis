"""SQL-backed data quality audit for the materialised MerRec event cache.

This is deliberately separate from `data.validate()`: Phase 0 answers "can this
analysis run?", while this audit answers "is the event log clean enough to trust
the portfolio numbers?" DuckDB lets us keep the checks declarative and close to
how an analyst would validate a warehouse table.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from _util import ROOT, df_to_md, load_config, write_md
from data import build_cohort
from personperiod import early_features, build_person_period, full_followup_users


EVENTS = ROOT / "data" / "events.parquet"


def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    con.execute("PRAGMA threads=4")
    path = str(EVENTS).replace("'", "''")
    con.execute(f"CREATE VIEW events AS SELECT * FROM read_parquet('{path}')")
    return con


def _one(con: duckdb.DuckDBPyConnection, sql: str):
    return con.execute(sql).fetchone()[0]


def _df(con: duckdb.DuckDBPyConnection, sql: str):
    return con.execute(sql).df()


def run(write: bool = True) -> dict:
    if not EVENTS.exists():
        raise SystemExit("data/events.parquet missing — run `make eda` first.")

    cfg = load_config()
    con = _con()
    expected = cfg["events"]["all_types"]
    conv = cfg["events"]["conversion"]

    summary = con.execute("""
        SELECT
          COUNT(*) AS n_events,
          COUNT(DISTINCT user_id) AS n_users,
          COUNT(DISTINCT session_id) AS n_sessions,
          MIN(stime) AS min_time,
          MAX(stime) AS max_time,
          DATE_DIFF('day', MIN(stime), MAX(stime)) AS span_days,
          COUNT(DISTINCT CASE WHEN event = ? THEN user_id END) AS n_converters
        FROM events
    """, [conv]).df()

    nulls = _df(con, """
        SELECT 'user_id' AS column_name, SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) AS null_rows FROM events
        UNION ALL SELECT 'stime', SUM(CASE WHEN stime IS NULL THEN 1 ELSE 0 END) FROM events
        UNION ALL SELECT 'session_id', SUM(CASE WHEN session_id IS NULL THEN 1 ELSE 0 END) FROM events
        UNION ALL SELECT 'item_id', SUM(CASE WHEN item_id IS NULL THEN 1 ELSE 0 END) FROM events
        UNION ALL SELECT 'event', SUM(CASE WHEN event IS NULL THEN 1 ELSE 0 END) FROM events
        UNION ALL SELECT 'c0_name', SUM(CASE WHEN c0_name IS NULL THEN 1 ELSE 0 END) FROM events
        UNION ALL SELECT 'c1_name', SUM(CASE WHEN c1_name IS NULL THEN 1 ELSE 0 END) FROM events
        UNION ALL SELECT 'brand_name', SUM(CASE WHEN brand_name IS NULL THEN 1 ELSE 0 END) FROM events
        UNION ALL SELECT 'price', SUM(CASE WHEN price IS NULL THEN 1 ELSE 0 END) FROM events
        ORDER BY null_rows DESC, column_name
    """)

    event_vocab = _df(con, """
        SELECT event, COUNT(*) AS rows, COUNT(DISTINCT user_id) AS users
        FROM events
        GROUP BY event
        ORDER BY rows DESC
    """)
    unexpected_events = con.execute("""
        SELECT event, COUNT(*) AS rows
        FROM events
        WHERE event NOT IN ({})
        GROUP BY event
        ORDER BY rows DESC
    """.format(",".join("?" for _ in expected)), expected).df()

    dup_rows = _one(con, """
        SELECT COALESCE(SUM(cnt - 1), 0)
        FROM (
          SELECT user_id, stime, session_id, item_id, event, COUNT(*) AS cnt
          FROM events
          GROUP BY 1,2,3,4,5
          HAVING COUNT(*) > 1
        )
    """)
    bad_price = _df(con, """
        SELECT
          SUM(CASE WHEN price < 0 THEN 1 ELSE 0 END) AS negative_price_rows,
          SUM(CASE WHEN price = 0 THEN 1 ELSE 0 END) AS zero_price_rows,
          MIN(price) AS min_price,
          APPROX_QUANTILE(price, 0.5) AS median_price,
          APPROX_QUANTILE(price, 0.99) AS p99_price,
          MAX(price) AS max_price
        FROM events
        WHERE price IS NOT NULL
    """)
    session_order = _df(con, """
        WITH s AS (
          SELECT session_id, COUNT(DISTINCT user_id) AS users, MIN(stime) AS start_time, MAX(stime) AS end_time
          FROM events
          GROUP BY session_id
        )
        SELECT
          SUM(CASE WHEN users > 1 THEN 1 ELSE 0 END) AS multi_user_sessions,
          SUM(CASE WHEN end_time < start_time THEN 1 ELSE 0 END) AS reversed_sessions,
          MAX(DATE_DIFF('hour', start_time, end_time)) AS max_session_span_hours
        FROM s
    """)
    scoped_sessions = _df(con, """
        SELECT
          COUNT(DISTINCT session_id) AS raw_session_ids,
          COUNT(*) AS user_scoped_sessions
        FROM (
          SELECT DISTINCT user_id, session_id
          FROM events
        )
    """)

    pandas_events = con.execute("SELECT user_id, stime, session_id, item_id, c0_name, c1_name, brand_name, price, event FROM events").df()
    cohort = build_cohort(pandas_events, cfg)
    feats = early_features(pandas_events, cohort, cfg)
    pp = build_person_period(pandas_events, cohort, feats, cfg)
    full_users = full_followup_users(pandas_events, cohort, cfg).intersection(pp["user_id"].unique())
    denominators = {
        "kept_after_left_truncation": int(cohort["kept"].sum()),
        "person_period_users": int(pp["user_id"].nunique()),
        "full_followup_users": int(len(full_users)),
        "partial_followup_users": int(pp["user_id"].nunique() - len(full_users)),
    }

    failures = []
    if int(nulls.loc[nulls["column_name"].isin(["user_id", "stime", "session_id", "event"]), "null_rows"].sum()) > 0:
        failures.append("required_nulls")
    if len(unexpected_events) > 0:
        failures.append("unexpected_event_values")
    if int(bad_price["negative_price_rows"].iloc[0] or 0) > 0:
        failures.append("negative_prices")
    if denominators["full_followup_users"] <= 0:
        failures.append("no_full_followup_users")

    warnings = []
    if int(dup_rows) > 0:
        warnings.append("duplicate_event_keys_present")
    if int(session_order["multi_user_sessions"].iloc[0] or 0) > 0:
        warnings.append("session_id_not_globally_unique")
    if int(nulls.loc[nulls["column_name"].isin(["brand_name", "c1_name"]), "null_rows"].sum()) > 0:
        warnings.append("optional_catalog_fields_missing")

    result = {
        "summary": summary,
        "nulls": nulls,
        "event_vocab": event_vocab,
        "unexpected_events": unexpected_events,
        "duplicate_rows": int(dup_rows),
        "bad_price": bad_price,
        "session_order": session_order,
        "scoped_sessions": scoped_sessions,
        "denominators": denominators,
        "pass": not failures,
        "failures": failures,
        "warnings": warnings,
    }
    if write:
        _write_report(result, expected)
    return result


def _write_report(r: dict, expected_events: list[str]) -> None:
    denom = r["denominators"]
    status = "PASS" if r["pass"] else "FAIL"
    L = [
        "# Data Quality Audit — MerRec event cache\n",
        f"> **Status: {status}.** DuckDB SQL로 `data/events.parquet`를 직접 검증했다. "
        "Phase-0는 분석 가능성 게이트이고, 이 문서는 데이터 클린룸 감사다.\n",
        "## 1. Table Summary\n",
        df_to_md(r["summary"], index=False, float_digits=1), "\n",
        "\n## 2. Required Fields / Missingness\n",
        df_to_md(r["nulls"], index=False, float_digits=0), "\n",
        "\n## 3. Event Vocabulary\n",
        f"Expected events from config: `{', '.join(expected_events)}`.\n",
        df_to_md(r["event_vocab"], index=False, float_digits=0), "\n",
    ]
    if len(r["unexpected_events"]):
        L += ["\nUnexpected event values:\n", df_to_md(r["unexpected_events"], index=False, float_digits=0), "\n"]
    else:
        L.append("\nUnexpected event values: none.\n")
    L += [
        "\n## 4. Integrity Checks\n",
        f"- Duplicate event keys (`user_id, stime, session_id, item_id, event`): **{r['duplicate_rows']:,}**\n",
        "- Price range:\n",
        df_to_md(r["bad_price"], index=False, float_digits=1), "\n",
        "- Session checks:\n",
        df_to_md(r["session_order"], index=False, float_digits=0), "\n",
        "- Session key scope:\n",
        df_to_md(r["scoped_sessions"], index=False, float_digits=0), "\n",
        "\nWarnings: " + (", ".join(f"`{w}`" for w in r["warnings"]) if r["warnings"] else "none") + ".\n",
        "\n## 5. Analysis Denominators\n",
        "| denominator | users |\n|---|---:|\n",
        f"| kept after left-truncation | {denom['kept_after_left_truncation']:,} |\n",
        f"| person-period users | {denom['person_period_users']:,} |\n",
        f"| full-follow-up users for binary summaries | {denom['full_followup_users']:,} |\n",
        f"| partial/right-censored near-end users | {denom['partial_followup_users']:,} |\n",
        "\n## Verdict\n",
    ]
    if r["pass"]:
        L.append("No blocking data-quality issue found. Required fields, event vocabulary, timestamp range, and prices are usable. "
                 "Duplicate event keys are retained as raw repeated interactions; `session_id` is treated as user-scoped rather than globally unique. "
                 "Known limitations are analytical, not raw-data corruption: no signup timestamp, no randomized exposure, and a 31-day observation window.\n")
    else:
        L.append("Blocking issues found: `" + "`, `".join(r["failures"]) + "`. Do not use headline reports until these are resolved.\n")
    L.append("\n_SQL hygiene: checks project only needed columns from parquet, aggregate before reporting, and avoid row-level exports._\n")
    write_md("docs/data_quality_report.md", "".join(L))


def main() -> int:
    r = run(write=True)
    print(f"[data_quality] wrote docs/data_quality_report.md ; PASS={r['pass']}")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
