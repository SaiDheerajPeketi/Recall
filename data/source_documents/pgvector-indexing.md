# Choosing and tuning pgvector indexes

## Exact and approximate search

Without an approximate index, pgvector performs exact nearest-neighbor search and therefore provides perfect recall for the queried rows. HNSW and IVFFlat trade some recall for speed. The query must order by a supported distance operator directly and include a `LIMIT` for the planner to use an approximate index in the normal nearest-neighbor pattern.

HNSW builds a multilayer graph. It generally provides a stronger speed-recall tradeoff than IVFFlat, but it takes longer to build and uses more memory. `m` controls the maximum connections per layer and `ef_construction` controls the candidate list during construction. At query time, increasing `hnsw.ef_search` can improve recall at the cost of latency. Set it locally in a transaction when only one query needs the change.

IVFFlat divides vectors into lists and probes only some lists at query time. It builds faster and uses less memory, but it needs representative data before index creation. As a starting point, the project documentation suggests roughly rows divided by 1,000 lists for up to one million rows and the square root of rows above that. Increasing `ivfflat.probes` improves recall but costs time. Setting probes to all lists yields exact behavior and can cause the planner not to use the index.

## Operational guidance

Create the correct operator-class index for the distance metric used by the query. Load initial data before building IVFFlat. Build production indexes concurrently when blocking writes is unacceptable. HNSW construction is much faster when the graph fits in `maintenance_work_mem`, but that setting must not be raised high enough to exhaust server memory. Monitor build progress with `pg_stat_progress_create_index` and use `EXPLAIN (ANALYZE, BUFFERS)` to verify the runtime plan.

When result quality changes after adding an approximate index, measure recall against an exact-search baseline before changing parameters.

