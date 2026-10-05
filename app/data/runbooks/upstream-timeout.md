# Upstream dependency timeout and gateway errors

## Symptoms and possible causes
HTTP 502 or 504 gateway errors and upstream request timeouts may follow a slow dependency, connection saturation, network disruption, or an unhealthy backend. Increased latency in a downstream payment or inventory API can exhaust callers. Correlation between a deployment and errors is a hypothesis to verify.

## Read-only investigation
Compare downstream dependency latency, error rates, and connection counts with caller metrics. Inspect sanitized trace IDs to locate which hop is slow. Compare configured connect and read timeout values across gateway and service boundaries. Check the upstream provider status and recent changes through approved channels. Do not place secrets, customer payloads, or access tokens in a shared incident report.

## Recovery decision and validation
Avoid adding unbounded retries because they can amplify overload. Ask service owners to assess bounded retries, circuit breaking, traffic reduction, or rollback before approving a change. Validate end-to-end latency and success rate rather than only the gateway health endpoint.
