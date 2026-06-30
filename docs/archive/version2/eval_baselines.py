#!/usr/bin/env python3
"""1막 v2 추천 베이스라인 실측 (POP / Markov-1) — leave-last-out.

속도 우선: 필요한 컬럼만 로드, item_id는 sampled-negative(199 neg) 평가.
타깃 단위: product_id (brand_c2, full-catalog), c1_id (full-catalog), item_id (sampled).
콜드/웜 분해는 product_id만. next-action(event_id) 다수결.
"""
import glob, time, math
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

t0 = time.time()
rng = np.random.default_rng(42)

K = 20
N_NEG = 199            # item_id sampled negatives
MAX_TEST_SESSIONS = 20000

DAY0 = pd.Timestamp('2023-05-01')
TRAIN_LO, TRAIN_HI = 0, 23     # session start day in [0,23]
TEST_LO, TEST_HI   = 27, 30    # session start day in [27,30]

COLS = ['user_id', 'stime', 'session_id', 'item_id', 'product_id', 'event_id', 'c1_id']

# ---- load ----
files = sorted(glob.glob('data/raw/2023*.parquet'))
df = pd.concat([pq.read_table(f, columns=COLS).to_pandas() for f in files], ignore_index=True)
print(f'[load] rows={len(df):,}  {time.time()-t0:.1f}s')

# session start day
sess_start = df.groupby('session_id')['stime'].transform('min')
df['day'] = (sess_start - DAY0).dt.days

train = df[(df['day'] >= TRAIN_LO) & (df['day'] <= TRAIN_HI)].copy()
test  = df[(df['day'] >= TEST_LO) & (df['day'] <= TEST_HI)].copy()
print(f'[split] train rows={len(train):,}  test rows={len(test):,}')

# order within session by time (stable)
train = train.sort_values(['session_id', 'stime'], kind='stable')
test  = test.sort_values(['session_id', 'stime'], kind='stable')


def build_pop(series):
    vc = series.value_counts()
    return vc.index.to_numpy(), vc.to_numpy()


def build_markov(seq_df, col):
    """train: prev->next 전이 카운트. dict[prev] -> dict[next]->count."""
    g = seq_df.groupby('session_id')[col]
    trans = {}
    for _, s in g:
        arr = s.to_numpy()
        for a, b in zip(arr[:-1], arr[1:]):
            d = trans.setdefault(a, {})
            d[b] = d.get(b, 0) + 1
    # precompute ranked-next per prev
    ranked = {}
    for a, d in trans.items():
        items = sorted(d.items(), key=lambda kv: -kv[1])
        ranked[a] = np.array([k for k, _ in items])
    return ranked


def test_pairs(seq_df, col):
    """leave-last-out: 세션 길이>=2(해당 col non-null 기준). returns list of (prev, target)."""
    sub = seq_df[['session_id', col]].dropna(subset=[col])
    pairs = []
    for sid, s in sub.groupby('session_id', sort=False):
        arr = s[col].to_numpy()
        if len(arr) >= 2:
            pairs.append((arr[-2], arr[-1]))
    return pairs


def metrics_from_ranks(ranks):
    """ranks: 1-based rank of target (np.inf if not in list). returns recall@K, ndcg@K, mrr."""
    ranks = np.asarray(ranks, dtype=float)
    hit = ranks <= K
    recall = hit.mean()
    ndcg = np.where(hit, 1.0 / np.log2(ranks + 1), 0.0).mean()
    mrr = np.where(np.isfinite(ranks), 1.0 / ranks, 0.0).mean()
    return recall, ndcg, mrr


def rank_of(target, ranked_list, pop_items, pos_in_pop, train_set):
    """full-catalog rank under POP-backoff Markov or pure POP.
    ranked_list = ordered candidate array (markov) or None for pure pop.
    pop_items: pop ranking; pos_in_pop: dict val->0-based pos.
    """
    if ranked_list is not None and len(ranked_list) > 0:
        # markov candidates first, then pop backfill (dedup)
        idx = np.where(ranked_list == target)[0]
        if len(idx):
            return idx[0] + 1
        # not in markov head -> backoff to pop ranking offset by len(markov head)
        offset = len(ranked_list)
        p = pos_in_pop.get(target)
        if p is None:
            return math.inf
        # account for markov items that also appear in pop (approx: just offset)
        return offset + p + 1
    else:
        p = pos_in_pop.get(target)
        return (p + 1) if p is not None else math.inf


def eval_fullcat(col, sample_n=None):
    pop_items, _ = build_pop(train[col].dropna())
    pos_in_pop = {v: i for i, v in enumerate(pop_items)}
    markov = build_markov(train, col)
    train_set = set(pop_items.tolist())

    pairs = test_pairs(test, col)
    if sample_n and len(pairs) > sample_n:
        idx = rng.choice(len(pairs), sample_n, replace=False)
        pairs = [pairs[i] for i in idx]

    pop_ranks, mk_ranks = [], []
    cold_pop, warm_pop = [], []   # by target membership in train (product_id only用)
    for prev, tgt in pairs:
        rp = rank_of(tgt, None, pop_items, pos_in_pop, train_set)
        rm = rank_of(tgt, markov.get(prev), pop_items, pos_in_pop, train_set)
        pop_ranks.append(rp); mk_ranks.append(rm)
        if tgt in train_set:
            warm_pop.append(rm)
        else:
            cold_pop.append(rm)
    res = {
        'n_pairs': len(pairs),
        'POP': metrics_from_ranks(pop_ranks),
        'Markov': metrics_from_ranks(mk_ranks),
        'warm_n': len(warm_pop), 'cold_n': len(cold_pop),
        'warm_Markov': metrics_from_ranks(warm_pop) if warm_pop else None,
        'cold_Markov': metrics_from_ranks(cold_pop) if cold_pop else None,
    }
    return res


def eval_sampled_item(sample_n=None):
    """item_id: 정답 + 199 랜덤 네거티브 풀에서 랭킹. 스코어=POP인기, Markov는 prev전이."""
    col = 'item_id'
    pop_items, pop_cnt = build_pop(train[col])
    pop_score = {v: c for v, c in zip(pop_items, pop_cnt)}
    catalog = pop_items  # negatives drawn from train catalog
    markov = build_markov(train, col)

    pairs = test_pairs(test, col)
    if sample_n and len(pairs) > sample_n:
        idx = rng.choice(len(pairs), sample_n, replace=False)
        pairs = [pairs[i] for i in idx]

    pop_ranks, mk_ranks = [], []
    cat_n = len(catalog)
    for prev, tgt in pairs:
        negs = catalog[rng.integers(0, cat_n, N_NEG)]
        cand = np.concatenate([[tgt], negs])  # tgt at index 0
        # POP score
        sc_pop = np.array([pop_score.get(c, 0) for c in cand], dtype=float)
        # rank of target (index0): higher score=better; ties broken random-ish via stable
        order = np.argsort(-sc_pop, kind='stable')
        rp = int(np.where(order == 0)[0][0]) + 1
        pop_ranks.append(rp)
        # Markov score: transition count prev->cand, backoff to pop
        mk = markov.get(prev)
        if mk is not None:
            mk_pos = {v: i for i, v in enumerate(mk)}
            sc_mk = np.array([(1e9 - mk_pos[c]) if c in mk_pos else pop_score.get(c, 0)
                              for c in cand], dtype=float)
        else:
            sc_mk = sc_pop
        order = np.argsort(-sc_mk, kind='stable')
        rm = int(np.where(order == 0)[0][0]) + 1
        mk_ranks.append(rm)
    return {'n_pairs': len(pairs),
            'POP': metrics_from_ranks(pop_ranks),
            'Markov': metrics_from_ranks(mk_ranks)}


def eval_next_action():
    """next-action: event_id 다수결. train 전체 최빈 이벤트 예측 + Markov(prev event)."""
    from sklearn.metrics import f1_score, accuracy_score
    col = 'event_id'
    # majority baseline
    maj = train[col].value_counts().idxmax()
    markov = build_markov(train, col)
    pairs = test_pairs(test, col)
    y_true, y_maj, y_mk = [], [], []
    for prev, tgt in pairs:
        y_true.append(tgt)
        y_maj.append(maj)
        mk = markov.get(prev)
        y_mk.append(mk[0] if mk is not None and len(mk) else maj)
    return {
        'n_pairs': len(pairs),
        'maj_acc': accuracy_score(y_true, y_maj),
        'maj_f1': f1_score(y_true, y_maj, average='macro'),
        'mk_acc': accuracy_score(y_true, y_mk),
        'mk_f1': f1_score(y_true, y_mk, average='macro'),
        'majority_class': maj,
    }


def fmt(m):
    if m is None:
        return 'n/a'
    r, n, mr = m
    return f'R@20={r:.4f} NDCG@20={n:.4f} MRR={mr:.4f}'


print('\n=== product_id (brand_c2, full-catalog) ===')
r_prod = eval_fullcat('product_id', MAX_TEST_SESSIONS)
print(f"n_pairs={r_prod['n_pairs']:,}")
print(' POP   ', fmt(r_prod['POP']))
print(' Markov', fmt(r_prod['Markov']))
print(f"  warm (n={r_prod['warm_n']:,}) Markov:", fmt(r_prod['warm_Markov']))
print(f"  cold (n={r_prod['cold_n']:,}) Markov:", fmt(r_prod['cold_Markov']))
print(f'  [t={time.time()-t0:.1f}s]')

print('\n=== c1_id (category, full-catalog) ===')
r_c1 = eval_fullcat('c1_id', MAX_TEST_SESSIONS)
print(f"n_pairs={r_c1['n_pairs']:,}")
print(' POP   ', fmt(r_c1['POP']))
print(' Markov', fmt(r_c1['Markov']))
print(f'  [t={time.time()-t0:.1f}s]')

print('\n=== item_id (sampled 199 neg) ===')
r_item = eval_sampled_item(MAX_TEST_SESSIONS)
print(f"n_pairs={r_item['n_pairs']:,}")
print(' POP   ', fmt(r_item['POP']))
print(' Markov', fmt(r_item['Markov']))
print(f'  [t={time.time()-t0:.1f}s]')

print('\n=== next-action (event_id) ===')
r_na = eval_next_action()
print(r_na)
print(f'  [t={time.time()-t0:.1f}s]')

print(f'\n[done] total {time.time()-t0:.1f}s')
