# Filtering approximate vector search

## Why filters can reduce results

With an approximate pgvector index, PostgreSQL can scan nearest candidates and then apply ordinary `WHERE` filters. If many candidates fail the filter, the query may return fewer rows than its `LIMIT` even when matching rows exist elsewhere. This is expected approximate-search behavior, not proof that the rows are absent.

Start by checking the actual plan, the selectivity of the filter, the index type, the query's distance operator, `LIMIT`, and the current search parameters. Compare the result with an exact-search baseline. For HNSW, increasing `hnsw.ef_search` makes more candidates available. For IVFFlat, increasing `ivfflat.probes` searches more lists. Both improve recall at a latency cost.

pgvector supports iterative index scans, which continue scanning when filtering removes too many candidates. Strict-order scans preserve exact distance ordering. Relaxed-order scans can provide better recall or performance with slightly relaxed ordering; a materialized common table expression can re-sort the returned rows when strict presentation order is needed. HNSW scan limits and memory multipliers, and IVFFlat maximum probes, bound the extra work.

## Structural options

When a filter has a small fixed set of values, partial vector indexes can isolate those values. Table partitioning can help when the data already has a sound partition key. A conventional index on the filter column may help the planner for selective exact searches, but PostgreSQL does not automatically combine every B-tree filter with an HNSW traversal.

Do not promise that one tuning value works for every tenant or predicate. Measure recall and latency across representative filter selectivities, and document the exact baseline, parameters, and result counts.

