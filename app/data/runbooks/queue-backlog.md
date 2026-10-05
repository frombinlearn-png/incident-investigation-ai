# Queue backlog and consumer lag

## Symptoms and possible causes
Growing queue depth, consumer lag, and message age can indicate that message production exceeds processing capacity. Consumer errors, poison messages, partition imbalance, or slow downstream writes can create a backlog. Stable throughput with a short burst may recover without a configuration change.

## Read-only investigation
Compare incoming and completed message rates, oldest message age, consumer utilization, retry counts, and dead-letter queue volume. Inspect sanitized failure samples for repeated poison messages. Check partition assignment and downstream write latency. Confirm business impact before changing delivery behavior.

## Recovery decision and validation
Do not purge queues or skip messages during initial triage. Ask the owning team to assess safe consumer scaling, isolated retries, and dead-letter handling while preserving ordering and idempotency requirements. Validate message age recovery and duplicate-processing metrics after an approved change.
