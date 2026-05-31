# Monitoring database activity

## Start with current activity

The `pg_stat_activity` view reports one row per server process and exposes the database, user, application name, client address, process state, query timing, wait event, and current or most recent query. A session marked `active` is executing a query. `idle in transaction` means the transaction remains open while the client is not issuing a query; this can retain locks and old row versions. Wait-event columns show that a process is waiting and identify the wait class, but a non-null wait event does not by itself mean the process is unhealthy.

Use timestamps to distinguish a long-running statement from a long-lived session. `backend_start` identifies when the connection began, `xact_start` identifies the current transaction start, and `query_start` identifies the current query start. Compare these values with the incident window instead of assuming the oldest session caused the problem.

## Investigate blocking

For lock contention, use `pg_blocking_pids(pid)` to identify sessions blocking a target process. Join those process IDs back to `pg_stat_activity` to inspect user, application, query, transaction age, and wait information. The function is safer than trying to reconstruct every lock conflict from `pg_locks`, although `pg_locks` remains useful for detailed inspection.

Before terminating a backend, confirm ownership, business impact, transaction state, and whether cancellation is sufficient. `pg_cancel_backend` asks the current query to stop; `pg_terminate_backend` ends the session. Termination can roll back work and interrupt applications, so it should be an explicit operator decision rather than an automatic recommendation.

Statistics are cumulative and can lag or reset. Record the observation time, PostgreSQL version, relevant settings, and query plan or log context before drawing a conclusion.

