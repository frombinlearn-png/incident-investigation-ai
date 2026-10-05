# AEM Dispatcher stale cache and content delivery

## Symptoms and possible causes
Adobe Experience Manager AEM pages may remain stale on publish delivery after content activation when Dispatcher cache invalidation is delayed or replication has failed. A CDN may also serve an older page. A mismatch between author, publish, Dispatcher, and CDN content does not identify the failing layer by itself.

## Read-only investigation
Compare the page version on author and publish using approved access. Check activation timestamps, replication queue status, and Dispatcher invalidation logs. Inspect cache response headers and CDN age for the affected path. Determine whether the problem affects one page, a subtree, or all content. Never expose an internal publish endpoint publicly to bypass cache.

## Recovery decision and validation
Avoid a full cache flush as an initial response because it can overload publish instances. Ask the AEM owner to assess a scoped invalidation or replication repair. Verify that the approved change reaches the affected content path and that publish load remains acceptable.
