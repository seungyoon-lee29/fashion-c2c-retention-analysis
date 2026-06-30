# Data Quality Audit — MerRec event cache
> **Status: PASS.** DuckDB SQL로 `data/events.parquet`를 직접 검증했다. Phase-0는 분석 가능성 게이트이고, 이 문서는 데이터 클린룸 감사다.
## 1. Table Summary
| n_events | n_users | n_sessions | min_time | max_time | span_days | n_converters |
| --- | --- | --- | --- | --- | --- | --- |
| 2771473 | 43311 | 494603 | 2023-05-01 00:00:00 | 2023-05-31 00:00:00 | 30 | 1923 |

## 2. Required Fields / Missingness
| column_name | null_rows |
| --- | --- |
| brand_name | 527210 |
| c1_name | 557 |
| c0_name | 0 |
| event | 0 |
| item_id | 0 |
| price | 0 |
| session_id | 0 |
| stime | 0 |
| user_id | 0 |

## 3. Event Vocabulary
Expected events from config: `item_view, item_like, item_add_to_cart_tap, offer_make, buy_start, buy_comp`.
| event | rows | users |
| --- | --- | --- |
| item_view | 2350839 | 42734 |
| item_like | 347972 | 22765 |
| item_add_to_cart_tap | 44793 | 9897 |
| offer_make | 18936 | 7386 |
| buy_start | 6185 | 2478 |
| buy_comp | 2748 | 1923 |

Unexpected event values: none.

## 4. Integrity Checks
- Duplicate event keys (`user_id, stime, session_id, item_id, event`): **2,466**
- Price range:
| negative_price_rows | zero_price_rows | min_price | median_price | p99_price | max_price |
| --- | --- | --- | --- | --- | --- |
| 0.0 | 0.0 | 1.0 | 25.0 | 640.4 | 5000.0 |
- Session checks:
| multi_user_sessions | reversed_sessions | max_session_span_hours |
| --- | --- | --- |
| 53890 | 0 | 18 |
- Session key scope:
| raw_session_ids | user_scoped_sessions |
| --- | --- |
| 494603 | 553395 |

Warnings: `duplicate_event_keys_present`, `session_id_not_globally_unique`, `optional_catalog_fields_missing`.

## 5. Analysis Denominators
| denominator | users |
|---|---:|
| kept after left-truncation | 33,671 |
| person-period users | 31,390 |
| full-follow-up users for binary summaries | 22,165 |
| partial/right-censored near-end users | 9,225 |

## Verdict
No blocking data-quality issue found. Required fields, event vocabulary, timestamp range, and prices are usable. Duplicate event keys are retained as raw repeated interactions; `session_id` is treated as user-scoped rather than globally unique. Known limitations are analytical, not raw-data corruption: no signup timestamp, no randomized exposure, and a 31-day observation window.

_SQL hygiene: checks project only needed columns from parquet, aggregate before reporting, and avoid row-level exports._
