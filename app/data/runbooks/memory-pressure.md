# Container memory pressure and OOMKilled restarts

## Symptoms and possible causes
OOMKilled events, exit code 137, rising resident memory, and repeated container restarts can indicate memory pressure. A low container memory limit, a leak, a workload burst, or unbounded caching may cause similar symptoms. Exit code 137 alone does not prove an out-of-memory kill; confirm the container termination reason.

## Read-only investigation
Compare working-set memory with the container memory limit and node capacity. Check restart counts, OOMKilled termination reasons, request volume, and recent deployments. Compare heap growth and garbage collection metrics over time if available. Ask the owner whether heap dumps can be collected safely; dumps can contain sensitive data and need controlled handling.

## Recovery decision and validation
Do not remove memory limits as a default fix. Ask the service owner to assess rollback, cache bounds, or an approved capacity change. Validate that memory stabilizes under comparable traffic and restart counts stop increasing. Preserve the incident timeline for a later root-cause investigation.
