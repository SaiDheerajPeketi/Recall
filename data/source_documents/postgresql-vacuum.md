# Routine vacuuming and table bloat

## Why vacuum is required

PostgreSQL uses multiversion concurrency control, so an update or delete leaves an old row version until no transaction can still see it. Routine vacuuming marks reusable space, updates planner statistics, maintains the visibility map, and prevents transaction ID wraparound. Standard `VACUUM` normally makes space reusable inside the table; it usually does not return that space to the operating system.

Autovacuum schedules `VACUUM` and `ANALYZE` based on per-table change thresholds. A busy table can outgrow default thresholds, while a long-running transaction, abandoned replication slot, or prepared transaction can prevent old row versions from becoming removable. Check table-level statistics, dead-tuple estimates, last vacuum times, autovacuum activity, transaction age, and server logs before changing settings.

## Safe response to rapid disk growth

First identify which database objects are growing with PostgreSQL size functions and operating-system measurements. Distinguish table and index growth from WAL retention, temporary files, logs, and unrelated filesystem use. Check for long-running transactions and replication lag. If autovacuum is falling behind on a specific high-write table, tune that table's vacuum scale factor, threshold, cost limits, or worker availability based on measured write volume.

Plain `VACUUM` is the lowest-risk maintenance step but may not shrink the file. `VACUUM FULL` rewrites the table, requires an exclusive lock, and needs additional disk space while it works. `REINDEX CONCURRENTLY` can address index bloat with less write blocking but still consumes resources and temporary disk. These disruptive operations require capacity checks, a maintenance plan, and monitoring.

Do not recommend deleting files from the PostgreSQL data directory. If free space is critically low or the source of growth is uncertain, preserve evidence and escalate before attempting a rewrite.

