# Reading query plans

## Explain before changing indexes

`EXPLAIN` shows the plan selected by the PostgreSQL optimizer. `EXPLAIN ANALYZE` executes the statement and adds actual row counts and timing, so it can change data for write statements and can impose the full cost of a slow query. Use an explicit transaction and rollback when analyzing data-changing statements, and avoid running an expensive plan on production without an impact assessment.

Compare estimated rows with actual rows at each node. Large differences often indicate stale statistics, correlated predicates, data skew, or an expression the planner cannot estimate well. Read from the most deeply nested nodes outward, paying attention to loops: a small per-loop cost may dominate when repeated many times. `BUFFERS` reports cache activity and temporary reads or writes, which helps separate CPU work from I/O pressure.

## Common next steps

If sequential scanning is unexpected, check table size, filter selectivity, available indexes, data types, operator classes, casts, and statistics before disabling planner features. A sequential scan can be correct when a query needs a large part of a table. If a sort spills, review the row count and sort method before increasing `work_mem`; that setting can be used by multiple operations in many concurrent sessions.

Capture the exact SQL shape with sensitive literals removed, PostgreSQL version, schema and index definitions, `EXPLAIN (ANALYZE, BUFFERS, SETTINGS)` output where safe, table statistics, and relevant configuration. Propose index changes only when the plan and workload show the expected benefit. Extra indexes consume storage and add write and vacuum cost.

Treat planner settings such as `enable_seqscan = off` as diagnostic aids, not durable fixes. A production recommendation should explain why the chosen plan is slow and how the proposed change addresses that cause.

