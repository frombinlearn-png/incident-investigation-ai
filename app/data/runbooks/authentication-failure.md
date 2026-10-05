# Authentication failures after token or secret rotation

## Symptoms and possible causes
A sudden increase in HTTP 401 unauthorized or 403 forbidden responses after credential rotation may indicate stale credentials, issuer mismatch, missing scopes, or clock skew. A 403 can also be a legitimate policy decision. Never copy access tokens, private keys, or client secrets into incident descriptions.

## Read-only investigation
Check error categories, token issuer and audience configuration, expiry time, and service clock synchronization without recording raw tokens. Compare deployment and secret rotation timestamps. Confirm required permissions with the identity owner. Use sanitized correlation IDs to investigate authentication logs.

## Recovery decision and validation
Do not disable authentication or broaden permissions to silence errors. Ask the identity and service owners to approve a configuration correction or credential refresh. Verify success using an authorized test identity and confirm unauthorized requests remain blocked.
