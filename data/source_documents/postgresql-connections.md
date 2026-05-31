# Connection timeouts and keepalives

## Separate connection establishment from session health

PostgreSQL exposes several timeout and TCP keepalive settings, and they solve different failure modes. `connect_timeout` is a client-side connection parameter: it limits how long the client waits while establishing a connection. `statement_timeout` cancels statements that run longer than the configured duration. `idle_in_transaction_session_timeout` terminates sessions that remain idle while holding an open transaction, which can otherwise retain locks and prevent vacuum cleanup. `idle_session_timeout` applies to sessions that are idle outside a transaction, but connection-pooling middleware may not react well to unexpected server-side closure.

Server-side TCP settings include `tcp_keepalives_idle`, `tcp_keepalives_interval`, and `tcp_keepalives_count`. They control when the operating system probes an otherwise idle TCP connection and how many failed probes are allowed before the connection is considered dead. `tcp_user_timeout` can limit how long transmitted data may remain unacknowledged. A zero value uses the operating-system default.

## Safe diagnostic sequence

When an application reports intermittent connection resets, first establish whether PostgreSQL restarted or logged a matching backend failure. Then collect the exact client error, database logs for the same timestamp, and network or load-balancer telemetry. Confirm whether the failure happens while connecting, during a query, or while a pooled connection is idle. Review client, pooler, server, operating-system, firewall, and load-balancer timeout settings together; changing a single keepalive value without that context can hide the original problem or increase detection time.

Do not present keepalive tuning as a root-cause fix when the evidence only proves that a connection ended. If database logs and network signals are unavailable, collect them and escalate to the team that owns database reliability or infrastructure.

