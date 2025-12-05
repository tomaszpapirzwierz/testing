# CCAAK Mock Exam - Detailed Explanations for Incorrect Answers

**Confluent Certified Administrator for Apache Kafka**
**Mock Examination Review**

---

## Overview

This document provides detailed explanations for the 22 questions you answered incorrectly on your CCAAK mock examination. Review these concepts carefully to improve your understanding before taking the actual exam.

**Your Score:** 38/60 (63.33%)
**Required to Pass:** 42/60 (70%)
**Gap to Close:** 4 questions

---

## Question 1 - Network Compression Configuration

**Your Answer:** d) Reduce the consumer fetch.min.bytes parameter
**Correct Answer:** a) Enable compression at the producer level using compression.type=gzip

### Explanation

To reduce network utilization between brokers and consumers, the most effective approach is to **enable compression at the producer level**. When a producer compresses messages before sending them to Kafka, those messages remain compressed in the broker's log files and are transmitted to consumers in compressed form. The consumer then decompresses the messages locally.

This approach reduces:
- Network bandwidth between producers and brokers
- Storage requirements on brokers
- Network bandwidth between brokers and consumers

Your answer (reducing fetch.min.bytes) would actually increase network requests by allowing the consumer to fetch smaller amounts of data more frequently, potentially increasing overall network utilization rather than reducing it.

**Key Configuration:** `compression.type=gzip` (or snappy, lz4, zstd)

---

## Question 6 - Consumer Group Rebalancing

**Your Answer:** a, c (session.timeout.ms too low, more partitions than consumers)
**Correct Answer:** a, b (session.timeout.ms too low, max.poll.interval.ms exceeded)

### Explanation

Consumer rebalances occur when the group coordinator believes a consumer has failed. The two most common configuration-related causes are:

**a) session.timeout.ms set too low:** If this timeout is shorter than the time needed for network communication or processing, the consumer may be kicked out of the group even though it's still functioning.

**b) max.poll.interval.ms exceeded:** If a consumer takes longer than this interval between poll() calls (usually due to slow message processing), the coordinator assumes the consumer is stuck and triggers a rebalance.

**Why option c is incorrect:** Having more partitions than consumers is a normal operational state. Extra partitions are simply distributed among available consumers (some consumers get multiple partitions). This does not cause rebalancing.

**Best Practices:**
- Set `session.timeout.ms` high enough to account for network delays (typically 10-45 seconds)
- Set `max.poll.interval.ms` based on your maximum processing time per batch

---

## Question 7 - SSL/TLS Configuration

**Your Answer:** a) security.protocol=SSL
**Correct Answer:** b) listeners=SSL://hostname:port

### Explanation

To enable SSL/TLS on a Kafka broker, you must configure the **listeners** property to specify the protocol and port. The correct format is:

```properties
listeners=SSL://hostname:9093
```

Or for multiple listeners:
```properties
listeners=PLAINTEXT://hostname:9092,SSL://hostname:9093
```

**Why your answer is incorrect:**
`security.protocol=SSL` is a **client-side configuration**, not a broker configuration. Clients use this to specify which protocol to use when connecting to brokers.

**Complete SSL Setup on Broker Requires:**
1. `listeners=SSL://hostname:port` - Defines the SSL listener
2. `ssl.keystore.location` - Path to keystore
3. `ssl.keystore.password` - Keystore password
4. `ssl.key.password` - Key password
5. `ssl.truststore.location` - Path to truststore (if using client authentication)
6. `ssl.truststore.password` - Truststore password

---

## Question 8 - min.insync.replicas Behavior

**Your Answer:** d) Majority of replicas (2 out of 3)
**Correct Answer:** b) 2 replicas (leader plus one follower)

### Explanation

When `min.insync.replicas=2` and a producer sends with `acks=all`, **exactly 2 replicas must acknowledge** the write - the leader plus at least 1 in-sync follower.

**How it works:**
- `acks=all` means wait for acknowledgment from all replicas in the ISR (In-Sync Replica set)
- `min.insync.replicas=2` sets the minimum ISR size required for writes to succeed
- The write succeeds when at least 2 replicas (leader + 1 follower) acknowledge

**Why option d is incorrect:**
Kafka doesn't use "majority" logic for acknowledgments. It uses the explicit `min.insync.replicas` value. Even with replication factor 3, only the number specified by `min.insync.replicas` needs to acknowledge when using `acks=all`.

**Example Scenarios:**
- RF=3, min.insync.replicas=2, acks=all → Requires 2 acknowledgments
- RF=5, min.insync.replicas=3, acks=all → Requires 3 acknowledgments
- RF=3, min.insync.replicas=3, acks=all → Requires all 3 acknowledgments

---

## Question 13 - Altering Topic Partitions

**Your Answer:** b) kafka-configs.sh with --alter --add-config partitions=6
**Correct Answer:** a) kafka-topics.sh with --alter --partitions 6

### Explanation

To increase the number of partitions for an existing topic, use the **kafka-topics.sh** tool with the `--alter` flag:

```bash
kafka-topics.sh --bootstrap-server localhost:9092 \
  --alter \
  --topic my-topic \
  --partitions 6
```

**Why your answer is incorrect:**
`kafka-configs.sh` is used for managing **dynamic broker and topic configurations** (like retention policies, cleanup policies, compression settings), not for structural changes like partition count.

**Important Notes:**
- You can only **increase** partition count, never decrease it
- Increasing partitions can affect message ordering guarantees within keys
- Existing messages won't be redistributed; only new messages use the new partitions

**kafka-configs.sh is used for settings like:**
```bash
kafka-configs.sh --alter --entity-type topics --entity-name my-topic \
  --add-config retention.ms=86400000
```

---

## Question 14 - In-Sync Replica (ISR) Characteristics

**Your Answer:** a, d (lag time and acks=all waiting for ISR)
**Correct Answer:** a, b (lag time and ISR eligibility for leader election)

### Explanation

**Option a (Correct):** A replica must stay caught up within `replica.lag.time.max.ms` (default 10 seconds) to remain in the ISR. If a follower falls behind by more than this time, it's removed from the ISR.

**Option b (Correct):** **Only replicas currently in the ISR are eligible to become partition leader.** This ensures the new leader has all committed messages. If `unclean.leader.election.enable=false` (default), an out-of-sync replica will never be elected leader.

**Option d (Your choice - Incorrect):** While true that producers with `acks=all` wait for ISR acknowledgment, this describes producer behavior, not a characteristic of the ISR itself.

**Option c (Incorrect):** The ISR is **dynamic** - it doesn't always include all replicas. Replicas fall in and out of the ISR based on their replication lag.

**ISR Lifecycle:**
1. Replica starts and begins fetching from leader
2. Once caught up (within `replica.lag.time.max.ms`), added to ISR
3. If replica falls behind, removed from ISR
4. If replica catches up again, re-added to ISR

---

## Question 15 - SASL/SCRAM Credential Storage

**Your Answer:** a) In a properties file on each broker
**Correct Answer:** b) In ZooKeeper as encrypted entries

### Explanation

When using **SASL/SCRAM authentication**, user credentials are stored **in ZooKeeper** (or in KRaft mode, in the metadata log), not in local broker files. This provides centralized credential management.

**Creating SCRAM credentials:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter \
  --add-config 'SCRAM-SHA-256=[password=secret],SCRAM-SHA-512=[password=secret]' \
  --entity-type users \
  --entity-name alice
```

These credentials are stored in ZooKeeper at: `/config/users/alice`

**Why this design:**
- **Centralized management:** All brokers access the same credential store
- **Dynamic updates:** Credentials can be added/modified without broker restart
- **Encryption:** Passwords are stored using SCRAM algorithms (salted challenge-response)

**Contrast with other authentication methods:**
- **SASL/PLAIN:** Passwords stored in broker's JAAS config file (your answer would apply here)
- **SASL/GSSAPI (Kerberos):** Uses external Kerberos KDC
- **SASL/SCRAM:** Uses ZooKeeper/KRaft metadata

---

## Question 18 - Consumer Lag Monitoring Metrics

**Your Answer:** a, c (records-lag per partition, commit-latency-avg)
**Correct Answer:** a, d (records-lag per partition, records-lag-max)

### Explanation

To effectively detect consumer lag issues, you should monitor:

**Option a (Correct):** `records-lag` per partition shows the number of records the consumer is behind for each partition it's assigned. This is the primary lag metric.

**Option d (Correct):** `records-lag-max` shows the maximum lag across all partitions assigned to the consumer. This single metric quickly identifies if any partition is falling behind significantly.

**Option c (Your choice - Incorrect):** `commit-latency-avg` measures how long it takes to commit offsets, not whether the consumer is lagging behind the producer. Low commit latency doesn't mean the consumer is keeping up with message production.

**Key Consumer Lag Metrics:**
```
kafka.consumer:type=consumer-fetch-manager-metrics,
  client-id=*,
  attribute=records-lag-max           # Maximum lag across all partitions

kafka.consumer:type=consumer-fetch-manager-metrics,
  partition=*,topic=*,client-id=*,
  attribute=records-lag               # Lag per partition
```

**Monitoring Best Practice:**
Alert when `records-lag-max` exceeds a threshold for an extended period, indicating the consumer cannot keep up with production rate.

---

## Question 19 - Enabling ACL Authorization

**Your Answer:** c) acl.enabled=true
**Correct Answer:** a) authorizer.class.name=kafka.security.auth.SimpleAclAuthorizer

### Explanation

To enable ACL-based authorization in Kafka, you must configure the **authorizer class** in the broker's server.properties:

**For Kafka 2.4+:**
```properties
authorizer.class.name=kafka.security.authorizer.AclAuthorizer
```

**For older Kafka versions:**
```properties
authorizer.class.name=kafka.security.auth.SimpleAclAuthorizer
```

**Why your answer is incorrect:**
`acl.enabled=true` is not a valid Kafka configuration parameter. ACLs are enabled by specifying the authorizer implementation class.

**Complete ACL Setup:**
1. Set the authorizer class (as above)
2. Configure authentication (SASL or SSL)
3. Create ACL rules using kafka-acls.sh:

```bash
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:alice \
  --operation Read \
  --topic my-topic
```

**Default Behavior:**
- Without an authorizer configured: All operations are allowed
- With an authorizer configured: All operations are denied unless explicitly permitted via ACLs

---

## Question 21 - Multi-Datacenter Replication Strategy

**Your Answer:** d) Equal distribution of replicas across all datacenters
**Correct Answer:** b) Asynchronous replication using MirrorMaker for cross-datacenter replication

### Explanation

For multi-datacenter Kafka deployments, the **best practice** is to use **asynchronous replication with MirrorMaker** (or MirrorMaker 2.0/Confluent Replicator) between datacenters, while maintaining synchronous replication within each datacenter.

**Why this provides the best balance:**

**Performance:**
- Synchronous cross-datacenter replication introduces high latency due to geographic distance
- Asynchronous replication doesn't block producers waiting for remote acknowledgments

**Durability:**
- Each datacenter maintains local replicas with synchronous replication
- Cross-datacenter replication provides disaster recovery
- If one datacenter fails, the other has a copy of the data

**Architecture:**
```
Datacenter 1                    Datacenter 2
+-----------------+            +-----------------+
| Kafka Cluster 1 |  ------>  | Kafka Cluster 2 |
| (3 brokers)     | MirrorMaker| (3 brokers)     |
| RF=3, local ISR |            | RF=3, local ISR |
+-----------------+            +-----------------+
```

**Why option d is incorrect:**
Distributing replicas equally across datacenters means synchronous replication across WAN links, which:
- Adds significant latency to every write
- Makes the cluster vulnerable to network partitions between datacenters
- Reduces throughput dramatically

---

## Question 25 - OfflinePartitionsCount Metric

**Your Answer:** c) Some partitions are not being replicated to all followers
**Correct Answer:** a) Some partitions have no leader and are unavailable for reads and writes

### Explanation

The `OfflinePartitionsCount` metric is **critical** - it indicates partitions that have **no active leader** and are therefore completely unavailable.

**What causes offline partitions:**
- All replicas in the ISR are down
- Leader failed and no eligible follower exists (when `unclean.leader.election.enable=false`)
- All brokers hosting the partition replicas have failed

**Impact:**
- **Complete unavailability:** Producers cannot write, consumers cannot read
- **Data loss risk:** If all replicas are lost permanently
- **Urgent action required:** This is a production-critical issue

**JMX Metric:**
```
kafka.controller:type=KafkaController,name=OfflinePartitionsCount
```

**Your answer (under-replicated partitions) is different:**
Under-replicated partitions still have a functioning leader and are available for reads/writes. They're monitored by:
```
kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions
```

**Recovery Actions:**
1. Investigate why brokers are down
2. Restart failed brokers if possible
3. If data loss is acceptable, enable unclean leader election temporarily

---

## Question 26 - Reducing Consumer Rebalance Time

**Your Answer:** a, d (increase session.timeout.ms, decrease heartbeat.interval.ms)
**Correct Answer:** b, d (use static membership, decrease heartbeat.interval.ms)

### Explanation

**Option b (Static Membership) - Correct:**
Setting `group.instance.id` enables **static membership**, which dramatically reduces rebalance time. With static membership:
- Consumer identity persists across restarts
- No rebalance triggered for temporary disconnections
- Partitions remain assigned during brief outages
- Rebalance only occurs after `session.timeout.ms` expires

```properties
group.instance.id=consumer-1
```

**Option d (Decrease heartbeat.interval.ms) - Correct:**
Smaller heartbeat intervals mean faster detection of consumer failures and quicker rebalances:
```properties
heartbeat.interval.ms=1000  # Send heartbeats every 1 second
```

**Why option a is incorrect:**
**Increasing** `session.timeout.ms` actually **increases** rebalance time for failed consumers. It takes longer to detect failures, so other consumers wait longer before taking over the failed consumer's partitions.

**Optimal Configuration for Fast Rebalances:**
```properties
session.timeout.ms=10000         # 10 seconds
heartbeat.interval.ms=3000       # 3 seconds (session.timeout/3)
group.instance.id=consumer-1     # Static membership
```

---

## Question 36 - Auto-Commit Behavior

**Your Answer:** a) Offsets are committed synchronously after each message is processed
**Correct Answer:** b) Offsets are committed asynchronously at intervals defined by auto.commit.interval.ms

### Explanation

When `enable.auto.commit=true` (the default), Kafka automatically commits offsets **periodically** and **asynchronously** in the background during `poll()` calls.

**How it works:**
```properties
enable.auto.commit=true
auto.commit.interval.ms=5000    # Commit every 5 seconds (default)
```

- Every time `poll()` is called, Kafka checks if `auto.commit.interval.ms` has elapsed
- If yes, it commits offsets for messages returned by the previous `poll()`
- Commits happen **asynchronously** (non-blocking)

**Why your answer is incorrect:**
Committing after every single message would be extremely inefficient and create massive overhead. Auto-commit batches offset commits at intervals.

**Important Implications:**

**At-least-once delivery:**
If a consumer crashes between commits, some messages may be reprocessed:
```
Time 0: poll() returns messages 1-100
Time 2: Consumer processes messages 1-50
Time 3: Consumer crashes (no commit happened)
Time 4: Consumer restarts, reads from offset 0, reprocesses messages 1-50
```

**For exactly-once processing:**
```properties
enable.auto.commit=false
```
Then manually commit after processing:
```java
consumer.commitSync();  // or commitAsync()
```

---

## Question 37 - ACL Enforcement Component

**Your Answer:** a) The ZooKeeper ensemble
**Correct Answer:** b) The broker's authorizer

### Explanation

**The broker's authorizer** is responsible for enforcing ACL rules, not ZooKeeper.

**How Kafka ACLs work:**

**1. Storage:** ACL rules are stored in ZooKeeper (or KRaft metadata log)

**2. Enforcement:** The **broker** enforces ACLs by:
   - Loading ACL rules from ZooKeeper/KRaft
   - Checking each client request against the authorizer
   - Allowing or denying the operation

**Architecture:**
```
Client Request
    ↓
Kafka Broker
    ↓
Authentication Layer (identifies the principal)
    ↓
Authorizer (checks ACLs for this principal)
    ↓
Allow/Deny Decision
```

**Why ZooKeeper doesn't enforce ACLs:**
ZooKeeper only **stores** the ACL configurations. Brokers read these rules and enforce them. ZooKeeper has no knowledge of Kafka's data plane operations (produce/consume requests).

**Authorizer Configuration:**
```properties
# In server.properties
authorizer.class.name=kafka.security.authorizer.AclAuthorizer
```

**ACL Check Flow:**
1. Client sends request with credentials
2. Broker authenticates client (extracts principal)
3. Broker's authorizer checks if principal has permission for the operation
4. Request allowed or denied

---

## Question 38 - File Handle Requirements

**Your Answer:** b, c (number of consumer groups, concurrent connections)
**Correct Answer:** a, c (number of partitions, concurrent connections)

### Explanation

Kafka brokers require file handles for:

**a) Number of partitions (Correct):**
Each partition requires multiple file handles:
- Log segment files (.log)
- Index files (.index)
- Time index files (.timeindex)

**Calculation example:**
- 1000 partitions × 3 files per partition = 3000+ file handles minimum
- Add more for rolled segments not yet deleted

**c) Concurrent connections (Correct):**
Each network connection (from producers, consumers, other brokers) requires file handles for:
- Socket connections
- Network buffers

**Why option b is incorrect:**
The **number of consumer groups** doesn't directly affect broker file handle usage. Consumer groups are logical concepts - the broker doesn't maintain open files per consumer group. What matters is the number of active **connections**, not groups.

**Production Recommendations:**

Check current limits:
```bash
ulimit -n
```

Increase file handle limits for Kafka:
```bash
# /etc/security/limits.conf
kafka soft nofile 100000
kafka hard nofile 100000
```

**Estimation formula:**
```
Required file handles =
  (partitions × 3) +           # Log, index, timeindex
  (connections × 1) +          # Socket handles
  1000                         # Buffer for other operations
```

---

## Question 48 - Kafka Quota Types

**Your Answer:** c) Request rate quota
**Correct Answer:** a) Network bandwidth quota (bytes/second)

### Explanation

Kafka supports **two primary types of quotas** that limit production/consumption rates:

**a) Network bandwidth quota (Correct):**
- Limits throughput in **bytes per second**
- Applies to produce and fetch requests
- Most commonly used for rate limiting

**Setting bandwidth quotas:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter \
  --add-config 'producer_byte_rate=1048576,consumer_byte_rate=2097152' \
  --entity-type users \
  --entity-name alice
```

This limits:
- Producer: 1 MB/s
- Consumer: 2 MB/s

**c) Request rate quota (Your answer):**
While Kafka does have **request rate quotas**, they limit the **percentage of time** spent handling requests, not the data rate. These are measured as a percentage of network/IO thread time, not requests/second.

**Quota Types Summary:**

| Quota Type | Unit | Purpose |
|------------|------|---------|
| producer_byte_rate | bytes/sec | Limit producer throughput |
| consumer_byte_rate | bytes/sec | Limit consumer throughput |
| request_percentage | % | Limit broker thread usage |
| connection_creation_rate | connections/sec | Limit new connections |

**Quota Enforcement:**
When a client exceeds its quota, the broker throttles by delaying responses, forcing the client to slow down.

---

## Question 52 - Network Thread Configuration

**Your Answer:** b) num.io.threads
**Correct Answer:** a) num.network.threads

### Explanation

Kafka uses two thread pools for request handling, and it's crucial to understand the difference:

**a) num.network.threads (Correct):**
- Handles **network I/O** (receiving requests, sending responses)
- Reads data from sockets
- Writes data to sockets
- Default: 3 threads

```properties
num.network.threads=8
```

**b) num.io.threads (Your answer):**
- Handles **disk I/O** (reading/writing log files)
- Processes the actual request logic
- Performs disk operations
- Default: 8 threads

```properties
num.io.threads=16
```

**Request Flow:**
```
Client Request
    ↓
[num.network.threads] ← Receive request from socket
    ↓
Request Queue
    ↓
[num.io.threads] ← Process request (disk I/O, log writes)
    ↓
Response Queue
    ↓
[num.network.threads] ← Send response to socket
```

**Tuning Guidelines:**

**Increase num.network.threads when:**
- High number of concurrent connections
- Network becomes the bottleneck
- CPU has spare capacity

**Increase num.io.threads when:**
- Disk I/O is slow
- Complex request processing
- Many partitions per broker

**Typical Production Values:**
```properties
num.network.threads=8   # 1 per CPU core typically
num.io.threads=16       # 2x num.network.threads
```

---

## Question 59 - Changing Replication Factor

**Your Answer:** a) Use kafka-topics.sh --alter --replication-factor 3
**Correct Answer:** c) Use kafka-reassign-partitions.sh to generate a reassignment plan with additional replicas

### Explanation

Unlike partition count, **replication factor cannot be changed directly** with kafka-topics.sh. You must use **kafka-reassign-partitions.sh** to manually reassign partitions with additional replicas.

**Correct Procedure:**

**Step 1: Create a reassignment JSON file:**
```json
{
  "version": 1,
  "partitions": [
    {
      "topic": "my-topic",
      "partition": 0,
      "replicas": [1, 2, 3]
    },
    {
      "topic": "my-topic",
      "partition": 1,
      "replicas": [2, 3, 1]
    }
  ]
}
```

**Step 2: Execute the reassignment:**
```bash
kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --execute
```

**Step 3: Verify completion:**
```bash
kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

**Why your answer doesn't work:**
```bash
# This command fails:
kafka-topics.sh --alter --replication-factor 3
# Error: replication factor cannot be changed
```

The `--replication-factor` flag in kafka-topics.sh only works during topic **creation**, not alteration.

**Alternative with Confluent Platform:**
If using Confluent, you can use:
```bash
confluent kafka topic update my-topic --replication-factor 3
```

---

## Question 60 - Producer Blocking Configuration

**Your Answer:** d) linger.ms
**Correct Answer:** a) max.block.ms

### Explanation

The `max.block.ms` configuration controls **how long the producer will block** when buffer memory is exhausted or metadata is unavailable.

**a) max.block.ms (Correct):**
Maximum time to block for:
- Waiting for buffer space when `buffer.memory` is full
- Waiting for metadata updates (topic/partition/leader information)

```properties
max.block.ms=60000  # Block up to 60 seconds (default)
```

**After timeout expires:**
```java
// Throws TimeoutException
producer.send(record);  // or producer.partitionsFor(topic)
```

**d) linger.ms (Your answer):**
This controls **how long to wait before sending a batch**, not how long to block. It's a performance optimization:

```properties
linger.ms=10  # Wait 10ms for more messages to batch together
```

**Key Producer Timeout Configurations:**

| Configuration | Purpose | Default |
|---------------|---------|---------|
| max.block.ms | Block waiting for metadata/buffer space | 60000 ms |
| request.timeout.ms | Wait for broker response | 30000 ms |
| delivery.timeout.ms | Total time for send (includes retries) | 120000 ms |
| linger.ms | Delay before sending batch | 0 ms |

**Blocking Scenarios:**

**Scenario 1 - Buffer full:**
```java
// Producer buffer is full, waits max.block.ms for space
producer.send(record);  // Blocks here
```

**Scenario 2 - Metadata unavailable:**
```java
// Leader information unknown, waits max.block.ms for metadata
producer.partitionsFor("new-topic");  // Blocks here
```

**Production Recommendation:**
Set `max.block.ms` based on your application's timeout tolerance. For real-time applications, keep it low (5-10 seconds). For batch processing, higher values (60+ seconds) are acceptable.

---

## Summary of Key Concepts to Review

Based on your incorrect answers, focus your study on these areas:

### 1. Security & Authentication
- SSL/TLS listener configuration
- SASL/SCRAM credential storage
- ACL authorization setup and enforcement

### 2. Replication & Durability
- ISR (In-Sync Replica) mechanics
- min.insync.replicas behavior
- Replication factor modification procedures

### 3. Consumer Configuration
- Rebalancing triggers and optimization
- Auto-commit behavior
- Static membership
- Lag monitoring metrics

### 4. Performance Tuning
- Compression strategies
- Thread pool configurations
- Network vs. disk I/O threads
- Producer blocking and timeout configurations

### 5. Operational Tasks
- Using kafka-topics.sh vs kafka-configs.sh
- Partition reassignment procedures
- Multi-datacenter replication strategies
- Quota types and configuration

### 6. Monitoring & Metrics
- Critical JMX metrics (OfflinePartitionsCount, UnderReplicatedPartitions)
- Consumer lag metrics
- File handle requirements

---

## Final Recommendations

You are **only 4 questions away** from passing the CCAAK exam. With focused review of the topics covered in this document, particularly:

1. **Hands-on practice** with Kafka CLI tools
2. **Deep dive into security configurations** (SSL, SASL, ACLs)
3. **Understanding JMX metrics** for monitoring
4. **Mastering consumer group mechanics** and rebalancing

You should be well-prepared to pass the actual CCAAK certification exam.

**Good luck with your preparation!**

---

*Document generated: 2025-12-05*
*Mock Exam Score: 38/60 (63.33%)*
*Target Score: 42/60 (70%)*
