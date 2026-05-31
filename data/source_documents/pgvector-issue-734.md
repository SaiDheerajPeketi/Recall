# Resolved issue: force an exact vector search for one query

## Reported problem

A pgvector user wanted to bypass an approximate index for a particular query without disabling indexes for the whole session. The goal was to guarantee exact behavior for the selected request while retaining approximate indexes for the normal workload.

## Maintainer resolution

The maintainer explained that the query can order by an expression that does not match the approximate index expression, such as adding zero to the computed distance. For IVFFlat, setting `ivfflat.probes` to the total number of lists is another route to exact behavior; at that setting PostgreSQL may choose not to use the index.

## Support guidance

Use this technique as a controlled comparison, not as a blanket performance recommendation. Run the approximate query and an exact baseline against the same snapshot and filter conditions, then compute whether the expected neighbors are missing. Record index type, distance operator, lists or HNSW settings, filter selectivity, `LIMIT`, plan, latency, and result identifiers.

If an exact query is required in production, test its cost at representative table size and concurrency. Exact scanning can be substantially slower, so a safe response should distinguish a diagnostic validation from a durable query path. Do not alter global planner settings or drop an index merely to obtain one exact comparison.

