# Database connection pool exhaustion

## Symptoms and possible causes
Database connection pool exhaustion can cause checkout latency, HTTP 503 errors, and acquisition timeouts. Typical log messages include pool exhausted, connection acquisition timeout, and too many connections. Possible causes include leaked connections, slow queries, long transactions, or an unexpected traffic increase. These symptoms do not prove which cause is active.

## Read-only investigation
Compare active, idle, and waiting database connections with the configured pool limit. Check connection acquisition duration, query latency, transaction age, and traffic before and after the incident. Review recent deployment changes to connection lifecycle handling. Ask the database owner to inspect long-running transactions and lock waits using approved read-only monitoring.

## Recovery decision and validation
Do not increase the database connection pool blindly: the database may already be at capacity. Escalate confirmed connection leaks or blocked transactions to the service and database owners. Any rollback, connection termination, or pool change requires operator approval and a recovery plan. Validate lower acquisition wait time and restored request success rate after an approved change.
