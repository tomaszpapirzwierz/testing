# CCAAK Mock Exam 6 (Advanced) - Detailed Explanations for Incorrect Answers

**Confluent Certified Administrator for Apache Kafka**
**Advanced Exam Review**

---

## Overview

This document provides detailed explanations for the 14 questions you answered incorrectly on your sixth CCAAK mock examination (Advanced Difficulty).

**Your Score:** 46/60 (76.67%) - PASSED
**Questions Missed:** 14/60
**Difficulty Level:** Advanced with multiple question formats

---

## Question 1 - Auto-Commit Timing

**Domain:** Apache Kafka Fundamentals
**Type:** Multiple-Choice

**Your Answer:** b, d (provided two answers for single-choice question)
**Correct Answer:** b) No offsets are committed because the interval hasn't elapsed

### Explanation

When a consumer crashes **before** the `auto.commit.interval.ms` has elapsed, **no offsets are committed**.

### How Auto-Commit Works

**Configuration:**
```properties
enable.auto.commit=true
auto.commit.interval.ms=5000  # 5 seconds
```

**Timeline:**
```
Time 0s: Consumer starts, poll() returns messages
Time 1s: Processing messages...
Time 2s: Processing messages...
Time 3s: Consumer CRASHES ← Before 5-second interval
Time 5s: (Never reached) Would have committed here
```

**Result:** No commit occurred, so on restart the consumer will re-read messages from the last committed offset.

### Detailed Auto-Commit Behavior

Auto-commit happens during `poll()` calls, not continuously:

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

    // Inside poll():
    // - Check if auto.commit.interval.ms has elapsed since last commit
    // - If yes: commit offsets for previously polled messages
    // - Then: return new messages

    processRecords(records); // Your application processes
}
```

**Key points:**
1. Auto-commit checks happen **at the start of poll()**
2. Commits are for messages from the **previous poll()**
3. If consumer crashes before next poll(), no commit occurs

### Example Scenario

**Setup:**
```properties
enable.auto.commit=true
auto.commit.interval.ms=5000
```

**Execution:**
```
00:00:00 - poll() returns messages 0-99
           (First poll, nothing to commit yet)
00:00:01 - Processing messages 0-99
00:00:02 - Processing messages 0-99
00:00:03 - CRASH! ← Consumer dies

On restart:
00:01:00 - Consumer starts
           Reads committed offset (none committed during crash)
           Re-reads messages 0-99
```

### Why Option d is Wrong

**Option d:** "Offsets are lost and the consumer must start from the beginning"

This is **incorrect** because:
- Offsets aren't "lost" - the last successful commit is still stored
- Consumer doesn't start from beginning - it starts from last committed offset
- If no commits ever happened, behavior depends on `auto.offset.reset`:
  - `auto.offset.reset=earliest` → Start from beginning
  - `auto.offset.reset=latest` → Start from end

### At-Least-Once vs. Exactly-Once

**Auto-commit provides at-least-once delivery:**

```
Scenario 1: Commit AFTER processing (safe but risk of duplicates)
poll() → process → crash → re-process on restart

Scenario 2: Commit BEFORE processing (risk of data loss)
poll() → commit → crash during processing → messages lost
```

**With enable.auto.commit=true:**
```
poll() ──> [auto-commit of previous batch] ──> return new messages ──> process

If crash during processing:
- Previous batch: committed ✓
- Current batch: NOT committed ✗
- Result: Current batch re-processed (duplicates possible)
```

### Manual Offset Management (Better Control)

For critical applications, use manual commits:

```java
// Disable auto-commit
Properties props = new Properties();
props.put("enable.auto.commit", "false");

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

    for (ConsumerRecord<String, String> record : records) {
        processRecord(record);
    }

    // Commit only after successful processing
    consumer.commitSync(); // or commitAsync()
}
```

### Auto-Commit Interval Tuning

**Short interval (1 second):**
```properties
auto.commit.interval.ms=1000
```
- **Pros:** Less re-processing on crash
- **Cons:** More commit overhead

**Long interval (30 seconds):**
```properties
auto.commit.interval.ms=30000
```
- **Pros:** Less commit overhead
- **Cons:** More re-processing on crash

**Default (5 seconds):**
```properties
auto.commit.interval.ms=5000
```
- Balanced between overhead and re-processing risk

### Key Takeaway

**Remember:**
- Auto-commit happens during `poll()` at intervals
- If consumer crashes **before** the interval, no commit occurs
- Last committed offset remains unchanged
- On restart, consumer re-reads from last commit (at-least-once)
- For exactly-once, disable auto-commit and use transactions

---

## Question 2 - Zero-Copy Optimization

**Domain:** Apache Kafka Fundamentals
**Type:** Multiple-Response

**Your Answer:** a, d (Zero-copy transfers without user space, requires special producer config)
**Correct Answer:** a, c or a, e (Zero-copy transfers without user space, improves consumer performance OR is disabled with SSL)

### Explanation

Zero-copy is a Kafka optimization that allows data transfer from disk to network without copying through the application's memory space.

### What is Zero-Copy?

**Traditional I/O (4 copies):**
```
Disk → Kernel buffer → User space buffer → Kernel socket buffer → NIC

4 copies:
1. Disk to kernel buffer (DMA)
2. Kernel buffer to user space (CPU copy)
3. User space to socket buffer (CPU copy)
4. Socket buffer to NIC (DMA)
```

**Zero-Copy (2 copies):**
```
Disk → Kernel buffer → NIC

2 copies:
1. Disk to kernel buffer (DMA)
2. Kernel buffer to NIC (via sendfile/splice system call)
```

**Savings:** Eliminates 2 CPU copies through user space!

### How Kafka Uses Zero-Copy

**Consumer reads:**
```java
// Kafka broker serves consumer fetch requests

// Traditional:
read(disk_file, buffer)           // Disk → Kernel → User space
write(socket, buffer)             // User space → Kernel → Network

// Zero-copy (what Kafka actually does):
sendfile(socket, disk_file)       // Disk → Kernel → Network (direct)
```

**Why this is fast:**
- No copying to/from JVM heap
- No context switching to user space
- Data stays in kernel page cache
- Dramatically reduces CPU usage

### The Correct Answers Explained

**Option a) TRUE ✓**
"Zero-copy allows data to be transferred from disk to network socket without copying to user space"

This is the **core concept** of zero-copy. Data goes directly from kernel buffer to network, bypassing application memory.

**Option c) TRUE ✓**
"Zero-copy improves consumer read performance by bypassing the JVM heap"

When consumers read, Kafka sends data directly from disk to network without loading into JVM heap:
- Reduces GC pressure
- Reduces memory usage
- Increases throughput

**Option e) TRUE ✓** (Alternative correct answer)
"Zero-copy is disabled when SSL/TLS encryption is enabled"

This is a **critical limitation**. With SSL:
- Data must be encrypted in user space
- Can't use sendfile() system call
- Must copy to user space for encryption
- Then copy back to kernel for transmission

**Performance impact:**
```
No SSL: sendfile() → zero-copy → high performance
With SSL: read → decrypt → process → encrypt → write → lower performance
```

### Why Your Answers Were Wrong

**Option d) FALSE ✗**
"Zero-copy requires special producer configuration to enable"

**Incorrect because:**
- Zero-copy is **automatic** for consumers reading from brokers
- No producer configuration needed
- No consumer configuration needed
- It's a broker-side optimization using operating system features
- Happens transparently when conditions are met

**What actually matters:**
- OS support (Linux sendfile/splice)
- No SSL/TLS (otherwise disabled)
- That's it!

**Option b) FALSE ✗**
"Zero-copy is only available when using compression"

**Incorrect because:**
- Zero-copy works with or without compression
- Compression happens before storage
- Zero-copy sends the stored data (compressed or not)
- They are independent optimizations

### Zero-Copy Availability Conditions

**Zero-copy is ENABLED when:**
- Operating system supports it (Linux, modern Unix)
- No SSL/TLS encryption
- Reading from disk (page cache)
- Consumer fetch requests

**Zero-copy is DISABLED when:**
- SSL/TLS is enabled
- Data must be transformed in application
- Windows (limited support)

### Performance Impact

**Benchmark example (Kafka consumer):**

```
Without zero-copy (SSL enabled):
- Throughput: 100 MB/s
- CPU usage: 80%
- Context switches: High

With zero-copy (no SSL):
- Throughput: 800 MB/s
- CPU usage: 20%
- Context switches: Low
```

**Real-world impact:**
- 8x throughput improvement
- 75% reduction in CPU usage
- Massive scaling benefits

### Code Perspective

**What Kafka does internally (simplified):**

```java
// Without zero-copy
byte[] data = readFromDisk(file);           // Disk → Kernel → User
writeToSocket(socket, data);                // User → Kernel → Network

// With zero-copy
long transferred = fileChannel.transferTo(
    position,                                // Start position
    count,                                   // Bytes to transfer
    socketChannel                           // Destination
);
// Directly uses sendfile() system call
// Disk → Kernel → Network (no user space)
```

### Zero-Copy and SSL Trade-off

**Production decision:**

**Option 1: Security first (SSL)**
```properties
security.protocol=SSL
# Result: No zero-copy, but encrypted
# Use when: Security is mandatory
```

**Option 2: Performance first (no SSL)**
```properties
security.protocol=PLAINTEXT
# Result: Zero-copy enabled, but no encryption
# Use when: Internal network, trusted environment
```

**Option 3: Compromise**
```properties
security.protocol=SASL_PLAINTEXT
# Result: Zero-copy enabled, authentication but no encryption
# Use when: Need auth, can tolerate unencrypted data
```

### Monitoring Zero-Copy

**Check if zero-copy is active:**

**OS level:**
```bash
# Check system calls
strace -p <kafka-pid> -e sendfile

# If you see sendfile() calls, zero-copy is working
# If you see read()+write() calls, it's not
```

**JMX metrics:**
```
# CPU usage
# Memory usage
# If CPU is low while throughput is high, zero-copy likely active
```

### Related Optimizations

**Kafka's other performance tricks:**

1. **Zero-copy:** Disk → Network (consumers)
2. **Page cache:** OS caches frequently read data
3. **Batch compression:** Compress multiple messages together
4. **Sequential I/O:** Write sequentially to disk
5. **Memory-mapped files:** In some cases

All work together for high performance!

### Key Takeaway

**Remember:**
- Zero-copy = Disk → Network without user space
- **Automatic** (no configuration needed)
- **Disabled** when SSL/TLS is enabled
- Improves consumer read performance dramatically
- Reduces CPU and memory usage
- Works with or without compression

The trade-off: Security (SSL) vs. Performance (zero-copy)

---

## Question 3 - Consumer Group Join Sequence

**Domain:** Apache Kafka Fundamentals
**Type:** Build List

**Your Answer:** C, A, E, B, D (Discover coordinator → JoinGroup → SyncGroup → Rebalance → Assignments)
**Correct Answer:** C, A, B, E, D (Discover coordinator → JoinGroup → Rebalance → SyncGroup → Assignments)

### Explanation

The rebalance is triggered **immediately after** the JoinGroup request, not after SyncGroup.

### The Correct Consumer Group Join Protocol

**C) Consumer discovers group coordinator**
**A) Consumer sends JoinGroup request**
**B) Group coordinator triggers rebalance**
**E) Consumer sends SyncGroup request**
**D) Consumers receive new partition assignments**

### Detailed Step-by-Step Flow

**Step C: Discover Group Coordinator**

The consumer first needs to find which broker is the group coordinator:

```
Consumer ──> Any Broker: FindCoordinator request
            (group.id = "my-consumer-group")

Broker ──> Consumer: Coordinator is Broker 2
```

The coordinator is determined by:
```
coordinator_broker = hash(group.id) % num_brokers
```

**Step A: Send JoinGroup Request**

Consumer sends JoinGroup to the coordinator:

```
Consumer ──> Coordinator: JoinGroup
{
  group_id: "my-consumer-group",
  member_id: "",  // Empty on first join
  protocol_type: "consumer",
  protocols: [RangeAssignor, RoundRobinAssignor]
}
```

**Step B: Coordinator Triggers Rebalance**

As soon as the coordinator receives JoinGroup:

```
Coordinator:
1. Detects new member joining
2. Increments generation_id
3. Triggers rebalance state
4. Waits for ALL group members to send JoinGroup
```

**Wait for all members:**
```
Coordinator waits up to rebalance.timeout.ms for all members
- Member 1: JoinGroup ✓
- Member 2: JoinGroup ✓
- Member 3: JoinGroup ✓
- All members joined → Proceed
```

**Step E: Send SyncGroup Request**

After ALL members have joined, coordinator responds:

```
Coordinator ──> Leader Consumer: JoinGroup Response
{
  generation_id: 5,
  leader_id: "consumer-1",
  members: [consumer-1, consumer-2, consumer-3],
  member_assignment: null  // Leader will compute
}

Coordinator ──> Follower Consumers: JoinGroup Response
{
  generation_id: 5,
  leader_id: "consumer-1",
  members: [],  // Followers don't get member list
  member_assignment: null
}
```

**Leader computes assignments:**
```java
// Leader consumer (consumer-1) computes assignments
Map<String, Assignment> assignments = assignor.assign(
  metadata,   // Topic partitions info
  members     // List of all consumers
);

// Result:
// consumer-1 → [partition-0, partition-1]
// consumer-2 → [partition-2, partition-3]
// consumer-3 → [partition-4, partition-5]
```

**All consumers send SyncGroup:**
```
Leader ──> Coordinator: SyncGroup
{
  generation_id: 5,
  member_id: "consumer-1",
  assignments: {
    consumer-1: [partition-0, partition-1],
    consumer-2: [partition-2, partition-3],
    consumer-3: [partition-4, partition-5]
  }
}

Followers ──> Coordinator: SyncGroup
{
  generation_id: 5,
  member_id: "consumer-2",  // or consumer-3
  assignments: {}  // Followers send empty
}
```

**Step D: Receive Partition Assignments**

Coordinator responds to each consumer with their assignment:

```
Coordinator ──> Consumer-1: SyncGroup Response
{
  assignment: [partition-0, partition-1]
}

Coordinator ──> Consumer-2: SyncGroup Response
{
  assignment: [partition-2, partition-3]
}

Coordinator ──> Consumer-3: SyncGroup Response
{
  assignment: [partition-4, partition-5]
}
```

### Why Your Order Was Incorrect

**Your order:** C, A, E, B, D
- You placed SyncGroup (E) **before** Rebalance (B)

**Problem:**
- SyncGroup **cannot happen before rebalance**
- Rebalance is triggered by JoinGroup
- SyncGroup is part of the rebalance protocol

**Timeline issues:**
```
Your order:
JoinGroup → SyncGroup → Rebalance ✗ (impossible)

Correct order:
JoinGroup → Rebalance triggered → SyncGroup ✓
```

### Complete Protocol Sequence

```
1. [C] FindCoordinator
   Consumer: "Who is the coordinator for my group?"

2. [A] JoinGroup (All members)
   Consumers: "We want to join the group"

3. [B] Rebalance Triggered
   Coordinator: "New member! Starting rebalance..."
   Coordinator: Waits for all members to rejoin

4. JoinGroup Responses
   Coordinator → Leader: "You're the leader, here are all members"
   Coordinator → Followers: "Wait for assignment from leader"

5. Assignment Computation
   Leader: Computes partition assignments

6. [E] SyncGroup (All members)
   Leader → Coordinator: "Here are the assignments for everyone"
   Followers → Coordinator: "What's my assignment?"

7. [D] Assignments Received
   Coordinator → All: "Here's your specific assignment"

8. Ready to Consume
   Consumers: Start fetching from assigned partitions
```

### State Machine View

```
Consumer State Machine:

INITIAL
  ↓
[C] FIND_COORDINATOR
  ↓
COORDINATOR_KNOWN
  ↓
[A] SEND_JOIN_GROUP
  ↓
[B] REBALANCING (waiting for all members)
  ↓
JOIN_GROUP_RESPONSE_RECEIVED
  ↓
[E] SEND_SYNC_GROUP
  ↓
[D] ASSIGNMENT_RECEIVED
  ↓
STABLE (consuming)
```

### Coordinator's Perspective

**Coordinator state transitions:**

```
1. Receive JoinGroup from consumer-1
   State: Empty → PreparingRebalance
   Action: Wait for more members (rebalance.timeout.ms)

2. Receive JoinGroup from consumer-2, consumer-3
   State: PreparingRebalance
   Action: All members joined

3. Send JoinGroup responses
   State: PreparingRebalance → AwaitingSync
   Action: Wait for SyncGroup from all

4. Receive SyncGroup from all members
   State: AwaitingSync
   Action: Extract assignments from leader

5. Send SyncGroup responses
   State: AwaitingSync → Stable
   Action: Rebalance complete
```

### Timing Considerations

**Configuration affecting join:**

```properties
# How long coordinator waits for all members to rejoin
rebalance.timeout.ms=300000  # 5 minutes

# How long coordinator waits after first JoinGroup
session.timeout.ms=45000     # 45 seconds

# How often consumers send heartbeats
heartbeat.interval.ms=3000   # 3 seconds
```

**Timeline example:**
```
00:00 - Consumer-1 sends JoinGroup
        Coordinator starts rebalance timer

00:01 - Consumer-2 sends JoinGroup
        Still waiting...

00:02 - Consumer-3 sends JoinGroup
        All members joined! Proceed to JoinGroup responses

00:02 - Coordinator sends JoinGroup responses
        Consumers compute/receive assignment info

00:03 - Consumers send SyncGroup
        Coordinator distributes assignments

00:03 - Rebalance complete
        Total time: 3 seconds
```

### Avoiding Rebalances

**Static Membership (reduces rebalances):**

```properties
group.instance.id=consumer-instance-1
```

With static membership:
- Consumer identity persists across restarts
- Short disconnects don't trigger rebalance
- Faster recovery from temporary failures

### Key Takeaway

**Correct sequence:**
1. **C** - Discover coordinator
2. **A** - Send JoinGroup
3. **B** - Rebalance triggered (coordinator side)
4. **E** - Send SyncGroup
5. **D** - Receive assignments

**Remember:** Rebalance (B) is triggered by JoinGroup (A), not after SyncGroup (E). SyncGroup is part of the rebalance process, not before it.

---

## Question 5 - Null Key Partitioning

**Domain:** Apache Kafka Fundamentals
**Type:** Multiple-Choice

**Your Answer:** b) The message is sent to partition 0 by default
**Correct Answer:** c) The message is distributed using a round-robin strategy across partitions

### Explanation

When a message has a **null key**, the default partitioner uses **round-robin** (or more precisely, sticky partitioner in Kafka 2.4+) to distribute messages, not always partition 0.

### Default Partitioner Behavior

**Kafka's DefaultPartitioner logic:**

```java
if (key == null) {
    // Null key: Use round-robin/sticky partitioner
    return stickyPartitionCache.partition(topic, cluster);
} else {
    // Non-null key: Hash-based partitioning
    return hash(keyBytes) % numPartitions;
}
```

### Null Key Behavior Evolution

**Kafka < 2.4 (Round-Robin):**
```java
// Strict round-robin for null keys
partition = (lastPartition + 1) % numPartitions

Example with 6 partitions:
Message 1 (key=null) → Partition 0
Message 2 (key=null) → Partition 1
Message 3 (key=null) → Partition 2
Message 4 (key=null) → Partition 3
Message 5 (key=null) → Partition 4
Message 6 (key=null) → Partition 5
Message 7 (key=null) → Partition 0 (wraps around)
```

**Kafka 2.4+ (Sticky Partitioner):**
```java
// Stick to one partition until batch is full
partition = stickyPartition

Example with 6 partitions:
Messages 1-100 (key=null)  → Partition 2 (batched)
Messages 101-200 (key=null) → Partition 5 (batched)
Messages 201-300 (key=null) → Partition 1 (batched)
```

**Why the change?**
- Better batching efficiency
- Reduced number of requests
- Improved throughput

### Why Option b is Wrong

**Option b:** "The message is sent to partition 0 by default"

**Incorrect because:**
- Kafka does **not** hard-code partition 0 for null keys
- This would create a hot spot (partition 0 overloaded)
- Would defeat the purpose of partitioning (load distribution)
- Goes against Kafka's design principles

**What if it always went to partition 0?**
```
6 partitions: 0, 1, 2, 3, 4, 5

All null-key messages → Partition 0 (overloaded)
Other partitions: 1, 2, 3, 4, 5 (idle)

Result:
- Imbalanced load
- Partition 0 becomes bottleneck
- Wasted capacity on other partitions
```

### Complete Partitioning Logic

**Case 1: Key is provided**
```java
ProducerRecord<String, String> record =
    new ProducerRecord<>("topic", "user123", "data");

// Partition = hash(keyBytes) % numPartitions
// Same key ALWAYS goes to same partition
// Preserves ordering for that key
```

**Case 2: Key is null**
```java
ProducerRecord<String, String> record =
    new ProducerRecord<>("topic", null, "data");

// Kafka 2.4+: Sticky partitioner (batch-aware round-robin)
// Kafka < 2.4: Pure round-robin
```

**Case 3: Explicit partition**
```java
ProducerRecord<String, String> record =
    new ProducerRecord<>("topic", 3, "key", "data");
                                 // ↑ Explicit partition

// Always goes to partition 3
// Key and partitioner are ignored
```

### Custom Partitioner

You can implement custom logic:

```java
public class CustomPartitioner implements Partitioner {
    @Override
    public int partition(String topic, Object key, byte[] keyBytes,
                        Object value, byte[] valueBytes, Cluster cluster) {
        if (key == null) {
            // Custom logic for null keys
            // Example: Always send to partition 0 (if you really want)
            return 0;
        } else {
            // Hash-based for non-null keys
            int numPartitions = cluster.partitionCountForTopic(topic);
            return Utils.toPositive(Utils.murmur2(keyBytes)) % numPartitions;
        }
    }
}

// Configure producer
props.put("partitioner.class", "com.example.CustomPartitioner");
```

### Sticky Partitioner Deep Dive (Kafka 2.4+)

**How it works:**

```java
class StickyPartitionCache {
    private int currentPartition = -1;

    public int partition(String topic, Cluster cluster) {
        if (currentPartition == -1 || shouldChangePartition()) {
            // Pick a new partition
            List<PartitionInfo> partitions = cluster.availablePartitionsForTopic(topic);
            int newPartition = random.nextInt(partitions.size());
            currentPartition = newPartition;
        }
        return currentPartition;
    }

    private boolean shouldChangePartition() {
        // Change partition when:
        // - Batch is full (batch.size reached)
        // - Linger time elapsed (linger.ms)
        return batchFull || lingerElapsed;
    }
}
```

**Benefits:**
```
Old round-robin (every message to different partition):
- 100 messages → 100 small batches → 100 requests → Inefficient

New sticky (many messages to same partition):
- 100 messages → 3 large batches → 3 requests → Efficient
```

**Performance impact:**
- 30-50% improvement in throughput
- Reduced CPU usage
- Better network utilization

### Real-World Example

**Scenario:** Logging system with null keys

**Kafka < 2.4:**
```
Message 1 → Partition 0
Message 2 → Partition 1
Message 3 → Partition 2
Message 4 → Partition 3
Message 5 → Partition 4
Message 6 → Partition 5
Message 7 → Partition 0
...
Result: Even distribution, many small batches
```

**Kafka 2.4+:**
```
Messages 1-500 → Partition 2 (one large batch)
Messages 501-1000 → Partition 4 (one large batch)
Messages 1001-1500 → Partition 1 (one large batch)
...
Result: Even distribution, fewer large batches
```

### Configuration Impact

**Producer configurations affecting partitioning:**

```properties
# Batch size (affects when partition changes)
batch.size=16384

# Linger time (affects when partition changes)
linger.ms=10

# Custom partitioner (completely changes logic)
partitioner.class=com.example.CustomPartitioner
```

### Monitoring Partition Distribution

**Check message distribution:**

```bash
# See message counts per partition
kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic my-topic \
  --time -1

# Output:
my-topic:0:10523
my-topic:1:10489
my-topic:2:10511
my-topic:3:10497
my-topic:4:10502
my-topic:5:10478
# Roughly even distribution
```

### When to Use Null Keys

**Good use cases:**
- Event logs (no natural grouping)
- Metrics (just want load balancing)
- Fire-and-forget messages

**Bad use cases:**
- Related events that need ordering
- Stateful processing requiring same key
- Compacted topics (key is required for compaction)

### Key Takeaway

**Remember:**
- Null keys → **Round-robin** or **sticky partitioner** (NOT partition 0)
- Kafka < 2.4: Pure round-robin
- Kafka 2.4+: Sticky partitioner (batch-aware round-robin)
- Non-null keys → Hash-based (consistent partition per key)
- Never assume partition 0 as default
- Distribution is designed for load balancing

---

## Question 8 - Empty ISR Scenarios

**Domain:** Apache Kafka Fundamentals
**Type:** Multiple-Response

**Your Answer:** a, d, c (All replicas crashed, network partition, min.insync.replicas too high)
**Correct Answer:** a, b, d (All replicas crashed, followers can't keep up, network partition)

### Explanation

An **empty ISR** (In-Sync Replica set) occurs when no replicas are able to keep up with the leader, including the leader itself when it's down.

### Understanding ISR (In-Sync Replica Set)

**ISR Definition:**
Replicas that are "caught up" with the leader within `replica.lag.time.max.ms`.

**Normal ISR:**
```
Topic: payments, Partition: 0
Leader: Broker 1
ISR: [1, 2, 3]  ← All 3 replicas in sync
```

**Empty ISR:**
```
Topic: payments, Partition: 0
Leader: none
ISR: []  ← No replicas in sync!
```

### Correct Scenarios for Empty ISR

**Option a) All replica brokers have crashed ✓**

```
Before:
Broker 1 (Leader): Running
Broker 2 (Follower): Running
Broker 3 (Follower): Running
ISR: [1, 2, 3]

Disaster (all crash):
Broker 1: CRASHED
Broker 2: CRASHED
Broker 3: CRASHED
ISR: []  ← Empty!

Result:
- Partition is OFFLINE
- No leader available
- Writes and reads fail
- OfflinePartitionsCount = 1
```

**Option b) Followers cannot keep up with leader due to slow disk I/O ✓**

```
Timeline:
00:00 - Leader writes at 100 MB/s
        Follower 1: Slow disk, only reads 10 MB/s
        Follower 2: Slow disk, only reads 10 MB/s

00:10 - Follower 1 falls behind > replica.lag.time.max.ms
        ISR shrinks: [1, 2, 3] → [1, 3]

00:20 - Follower 2 also falls behind
        ISR shrinks: [1, 3] → [1]

00:30 - Leader has disk failure or gets overwhelmed
        Leader also fails
        ISR shrinks: [1] → []

Result: Empty ISR
```

**Why this happens:**
- Disk I/O bottleneck on followers
- Followers fall out of ISR
- Eventually leader also fails
- No replicas remain in sync

**Option d) Network partition between leader and all followers ✓**

```
Network Partition:

[Broker 1 - Leader]  ←  Network partition
                     ✗
[Broker 2, 3 - Followers]

From Leader's perspective:
- Followers not responding
- Remove followers from ISR after replica.lag.time.max.ms
- ISR: [1, 2, 3] → [1]

If Leader also gets isolated completely:
- Leader can't reach ZooKeeper
- Leader demoted
- ISR: [1] → []

Result: Empty ISR
```

### Why Option c is Wrong

**Option c) The topic has min.insync.replicas set too high ✗**

**Incorrect because:**
- `min.insync.replicas` **does not affect ISR membership**
- ISR is based on replication lag, not configuration
- `min.insync.replicas` only affects **write acceptance**

**What min.insync.replicas actually does:**
```
min.insync.replicas=2
ISR: [1, 2, 3]  ← 3 replicas in sync

Producer writes with acks=all:
- Requires ISR.size >= min.insync.replicas
- Requires 3 >= 2 ✓
- Write succeeds

If ISR shrinks to [1]:
- ISR.size < min.insync.replicas
- 1 < 2 ✗
- Write fails with NOT_ENOUGH_REPLICAS
- But ISR is [1], not empty []
```

**min.insync.replicas affects writes, not ISR:**

| Config | ISR State | Write Result |
|--------|-----------|--------------|
| min.insync.replicas=2 | ISR=[1,2,3] | Success |
| min.insync.replicas=2 | ISR=[1,2] | Success |
| min.insync.replicas=2 | ISR=[1] | NOT_ENOUGH_REPLICAS |
| min.insync.replicas=2 | ISR=[] | NOT_LEADER_OR_FOLLOWER |

**ISR becomes empty due to:**
- Physical failures (brokers crash)
- Network issues (can't communicate)
- Resource issues (can't keep up)

**NOT because of configuration!**

### Additional Scenarios (Not in Options)

**Scenario: Leader removed from ISR (rare)**
```
1. Leader writes message M1
2. Leader ACKs producer
3. Leader crashes before followers replicate M1
4. Followers don't have M1
5. New leader elected (follower)
6. Old leader restarts
7. Old leader's M1 is truncated (not in new leader)
8. Old leader joins as follower
9. If all brokers fail before old leader catches up: Empty ISR
```

**Scenario: ZooKeeper partition**
```
1. All brokers lose connection to ZooKeeper
2. No controller can be elected
3. No leader elections can happen
4. ISR information cannot be updated
5. Eventually: Empty ISR state
```

### ISR Management Configuration

```properties
# How long a follower can be behind before removal from ISR
replica.lag.time.max.ms=10000  # 10 seconds (default)

# Follower fetch settings
replica.fetch.min.bytes=1
replica.fetch.max.bytes=1048576
replica.fetch.wait.max.ms=500
```

### Monitoring ISR Health

**JMX Metrics:**
```
# Partitions under-replicated (ISR < replication.factor)
kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions

# Partitions with no leader (ISR empty)
kafka.controller:type=KafkaController,name=OfflinePartitionsCount

# ISR shrink rate
kafka.server:type=ReplicaManager,name=IsrShrinksPerSec
```

**CLI Check:**
```bash
kafka-topics.sh --describe \
  --topic my-topic \
  --bootstrap-server localhost:9092

# Look for:
# Isr: []  ← Empty ISR (bad!)
# Isr: [1,2,3]  ← Healthy ISR (good)
```

### Recovery from Empty ISR

**Option 1: Wait for brokers to recover**
```bash
# Start failed brokers
systemctl start kafka

# Brokers rejoin, sync data, ISR rebuilds
```

**Option 2: Unclean leader election (data loss risk)**
```properties
# Enable unclean election (DANGER!)
unclean.leader.election.enable=true
```

This allows out-of-sync replica to become leader:
- Gets partition online
- But may lose messages
- Use only as last resort

**Option 3: Manual intervention**
```bash
# If data loss acceptable, trigger leader election
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type unclean \
  --topic my-topic \
  --partition 0
```

### Preventing Empty ISR

**Best practices:**

1. **Sufficient replicas:**
```properties
replication.factor=3  # Can lose 2 brokers
min.insync.replicas=2  # Need 2 for writes
```

2. **Monitor broker health:**
```bash
# Alert on UnderReplicatedPartitions
# Alert on OfflinePartitionsCount
```

3. **Rack awareness:**
```properties
broker.rack=rack1
# Distributes replicas across racks
```

4. **Resource provisioning:**
```
# Ensure brokers have:
- Sufficient disk I/O
- Adequate network bandwidth
- Enough CPU/memory
```

5. **Gradual replication factor:**
```
# Start with RF=3
# If cluster is stable, can tolerate RF=2
# Never use RF=1 in production
```

### Key Takeaway

**ISR becomes empty when:**
- ✓ All replica brokers crash
- ✓ Followers can't keep up due to resource issues
- ✓ Network partition isolates all replicas
- ✗ NOT because min.insync.replicas is set too high

**Remember:**
- ISR = replicas that are caught up (based on replication lag)
- min.insync.replicas = minimum required for writes (doesn't control ISR)
- Empty ISR = partition offline = critical outage
- Monitor UnderReplicatedPartitions and OfflinePartitionsCount

---

*(Continuing with remaining questions...)*

## Question 9 - fetch.max.wait.ms Purpose

**Domain:** Apache Kafka Fundamentals
**Type:** Multiple-Choice

**Your Answer:** c) Maximum time to wait for the broker to acknowledge offset commits
**Correct Answer:** a) Maximum time the consumer will wait for min.bytes of data before returning

### Explanation

The `fetch.max.wait.ms` configuration controls how long the **broker** will wait to accumulate `fetch.min.bytes` of data before responding to a consumer's fetch request.

### What fetch.max.wait.ms Does

```properties
fetch.min.bytes=1024        # 1 KB minimum
fetch.max.wait.ms=500       # 500 ms maximum wait
```

**Consumer fetch logic:**
```
Consumer → Broker: Fetch request (give me data)
                   "I want at least 1 KB (fetch.min.bytes)"

Broker logic:
IF (data available >= 1 KB):
    Return data immediately
ELSE:
    Wait up to 500 ms (fetch.max.wait.ms)
    IF (accumulated >= 1 KB):
        Return data
    ELSE IF (timeout reached):
        Return whatever is available (even if < 1 KB)
```

### Detailed Fetch Flow

**Scenario 1: Plenty of data available**
```
Time 0ms: Consumer sends fetch request (min=1KB, max_wait=500ms)
Time 0ms: Broker has 10 KB available
Time 0ms: Broker returns 10 KB immediately
          (No waiting because min.bytes already satisfied)
```

**Scenario 2: Not enough data, wait helps**
```
Time 0ms: Consumer sends fetch request (min=1KB, max_wait=500ms)
Time 0ms: Broker has 200 bytes (< 1 KB)
          Broker waits...
Time 150ms: More data arrives, now 1.2 KB total
Time 150ms: Broker returns 1.2 KB
            (Waited 150ms, got enough data)
```

**Scenario 3: Timeout before enough data**
```
Time 0ms: Consumer sends fetch request (min=1KB, max_wait=500ms)
Time 0ms: Broker has 200 bytes
          Broker waits...
Time 500ms: Timeout! Still only 300 bytes
Time 500ms: Broker returns 300 bytes anyway
            (Waited full 500ms, timeout forces return)
```

### Why Your Answer Was Wrong

**Your answer:** "Maximum time to wait for the broker to acknowledge offset commits"

**Why this is incorrect:**
- `fetch.max.wait.ms` is about **fetching messages**, not **committing offsets**
- Offset commits are controlled by different configurations
- Offset commit timeout would be in producer config, not fetch config

**Offset commit configurations (different):**
```properties
# Consumer offset commit timeout
request.timeout.ms=30000     # How long to wait for offset commit response

# Auto commit interval
auto.commit.interval.ms=5000 # How often to auto-commit
```

### Complete Fetch Configuration

```properties
# Minimum bytes to fetch
fetch.min.bytes=1024

# Maximum wait time for min.bytes
fetch.max.wait.ms=500

# Maximum bytes to fetch
fetch.max.bytes=52428800     # 50 MB

# Per-partition fetch limit
max.partition.fetch.bytes=1048576  # 1 MB
```

### Tuning Guidance

**Low latency (real-time applications):**
```properties
fetch.min.bytes=1           # Don't wait for batching
fetch.max.wait.ms=100       # Short timeout
```
- Consumer gets data ASAP
- More requests, higher overhead
- Lower latency

**High throughput (batch processing):**
```properties
fetch.min.bytes=102400      # Wait for 100 KB
fetch.max.wait.ms=1000      # 1 second timeout
```
- Fewer requests, larger batches
- More efficient
- Higher latency acceptable

**Default (balanced):**
```properties
fetch.min.bytes=1
fetch.max.wait.ms=500
```

### Relationship with Producer linger.ms

**Similar concept, opposite direction:**

**Producer (linger.ms):**
```properties
linger.ms=10
# Producer waits up to 10ms to batch messages before sending
```

**Consumer (fetch.max.wait.ms):**
```properties
fetch.max.wait.ms=500
# Broker waits up to 500ms to batch data before returning to consumer
```

Both are about batching for efficiency!

### Key Takeaway

**Remember:**
- `fetch.max.wait.ms` = How long **broker waits** for min.bytes before returning
- About **fetching data**, not committing offsets
- Trade-off: latency vs. throughput
- Works together with `fetch.min.bytes`

---

## Question 11 - ACL Configuration Order

**Domain:** Apache Kafka Security
**Type:** Build List

**Your Answer:** B, D, A, C, E (Configure producer → Describe ACL → Write ACL → Enable authorizer → Test)
**Correct Answer:** C, D, A, B, E (Enable authorizer → Describe ACL → Write ACL → Configure producer → Test)

### Explanation

You must **enable the authorizer on the broker FIRST** before creating ACLs. Otherwise, ACLs have no effect.

### Correct Setup Order

**C) Enable the authorizer on the broker**
**D) Create ACL for Describe operation**
**A) Create ACL for Write operation**
**B) Configure the producer with credentials**
**E) Test producer can send messages**

### Why Order Matters

**Step C: Enable Authorizer (MUST BE FIRST)**

Without enabling the authorizer, ACLs are not enforced!

```properties
# In server.properties
authorizer.class.name=kafka.security.authorizer.AclAuthorizer

# Restart broker for this to take effect
```

**Why first:**
- ACLs are useless if no authorizer is checking them
- Like creating a lock but never installing the door
- Broker must be restarted with authorizer enabled

**Step D: Create Describe ACL**

Producers need Describe to get topic metadata:

```bash
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:myproducer \
  --operation Describe \
  --topic my-topic
```

**Why Describe is needed:**
- Producer needs to know partition count
- Producer needs to know partition leaders
- Without Describe: Producer can't even find the topic

**Step A: Create Write ACL**

Now allow the actual write operation:

```bash
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:myproducer \
  --operation Write \
  --topic my-topic
```

**Step B: Configure Producer**

Producer must authenticate to use these ACLs:

```properties
# Producer config
bootstrap.servers=localhost:9092
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-256
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
  username="myproducer" \
  password="secret";
```

**Step E: Test**

Now verify it works:

```bash
kafka-console-producer.sh \
  --broker-list localhost:9092 \
  --topic my-topic \
  --producer.config producer.properties
```

### Why Your Order Was Wrong

**Your order:** B, D, A, C, E

**Problem 1:** You configured producer (B) before enabling authorizer (C)
- Producer configuration is pointless if authorizer isn't even enabled yet

**Problem 2:** You created ACLs (D, A) before enabling authorizer (C)
- ACLs are stored but have no effect
- Like writing rules before establishing the rule enforcement system

**Correct logic:**
```
1. Enable enforcement (authorizer)
2. Create rules (ACLs)
3. Configure clients (producer)
4. Test
```

### Complete ACL Setup Example

**1. Enable authorizer (restart required):**
```properties
# server.properties
authorizer.class.name=kafka.security.authorizer.AclAuthorizer
```

```bash
systemctl restart kafka
```

**2. Create ACLs:**
```bash
# Describe (metadata)
kafka-acls.sh --add \
  --allow-principal User:myproducer \
  --operation Describe \
  --topic my-topic \
  --bootstrap-server localhost:9092

# Write (produce)
kafka-acls.sh --add \
  --allow-principal User:myproducer \
  --operation Write \
  --topic my-topic \
  --bootstrap-server localhost:9092

# Create (if producer should create topics)
kafka-acls.sh --add \
  --allow-principal User:myproducer \
  --operation Create \
  --cluster \
  --bootstrap-server localhost:9092
```

**3. Configure producer:**
```properties
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-256
ssl.truststore.location=/path/to/truststore.jks
ssl.truststore.password=password
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username="myproducer" password="secret";
```

**4. Test:**
```bash
echo "test message" | kafka-console-producer.sh \
  --broker-list localhost:9092 \
  --topic my-topic \
  --producer.config producer.properties
```

### What Happens Without Authorizer

**No authorizer configured:**
```properties
# server.properties (no authorizer)
# authorizer.class.name is not set
```

```bash
# ACLs are created but...
kafka-acls.sh --add --allow-principal User:alice --operation Write --topic test

# All users can still write! ACLs ignored.
# No authorization enforcement
```

### Default Behavior

**With authorizer, no ACLs:**
```
Authorizer: ENABLED
ACLs: NONE

Result: ALL operations DENIED
```

**Without authorizer:**
```
Authorizer: DISABLED
ACLs: ANY

Result: ALL operations ALLOWED
```

### Key Takeaway

**Setup order:**
1. Enable authorizer (broker config, restart required)
2. Create ACLs (Describe + Write for producer)
3. Configure client with credentials
4. Test

**Remember:** You can't enforce rules if you haven't installed the rule enforcer!

---

## Question 17 - SSL Endpoint Identification Algorithm

**Domain:** Apache Kafka Security
**Type:** Multiple-Choice

**Your Answer:** a) It defaults to an empty string, requiring manual configuration
**Correct Answer:** b) It defaults to "https" to enable hostname verification

### Explanation

The `ssl.endpoint.identification.algorithm` configuration **defaults to "https"** which automatically enables hostname verification for SSL/TLS connections. This is a critical security feature that prevents man-in-the-middle (MITM) attacks.

### What is Endpoint Identification?

**Endpoint identification = Hostname verification**

When a Kafka client (producer/consumer/broker) connects to a broker over SSL:

```
1. TCP connection established
2. TLS handshake begins
3. Server presents SSL certificate
4. Client validates certificate:
   a) Is it signed by trusted CA? ✓
   b) Is it expired? ✓
   c) Does hostname match certificate CN/SAN? ← Endpoint identification
```

### Default Behavior (Secure)

```properties
# Default configuration (you don't need to set this)
ssl.endpoint.identification.algorithm=https
```

**What happens:**
```
Client connects to: kafka-broker-1.example.com:9093

Server presents certificate:
  CN=kafka-broker-1.example.com
  SAN=kafka-broker-1.example.com, kafka-broker-1

Client checks:
  Hostname "kafka-broker-1.example.com" matches CN ✓
  Connection accepted
```

### Why Your Answer Was Wrong

**Your answer:** "It defaults to an empty string, requiring manual configuration"

**Incorrect because:**
- Modern Kafka (2.0+) defaults to `"https"`, not empty string
- Empty string would **disable** hostname verification (insecure)
- No manual configuration needed for secure default behavior
- Kafka enables security by default

**Historical context:**
- Kafka < 2.0: Default was empty string (insecure)
- Kafka >= 2.0: Default is "https" (secure)
- This was a **security enhancement**

### Configuration Options

**Option 1: Default (Recommended - Secure)**
```properties
# Don't set anything, defaults to "https"
ssl.endpoint.identification.algorithm=https
```
- Hostname verification enabled
- Prevents MITM attacks
- Production recommended

**Option 2: Explicit https**
```properties
ssl.endpoint.identification.algorithm=https
```
- Same as default
- Explicit is clearer for documentation

**Option 3: Disabled (Dangerous)**
```properties
ssl.endpoint.identification.algorithm=
```
- Empty string disables verification
- Accepts any certificate
- **NEVER use in production**
- Only for testing/development

### Security Implications

**With hostname verification (default):**

```
Attacker intercepts connection:
  Client expects: kafka-broker-1.example.com
  Attacker presents cert for: attacker.com

Client checks:
  "kafka-broker-1.example.com" != "attacker.com" ✗
  Connection REJECTED

Result: Attack prevented ✓
```

**Without hostname verification (empty string):**

```
Attacker intercepts connection:
  Client expects: kafka-broker-1.example.com
  Attacker presents cert for: attacker.com

Client checks:
  Hostname verification disabled
  Connection ACCEPTED

Result: MITM attack succeeds ✗
```

### Certificate Subject Alternative Names (SAN)

**Proper certificate setup:**

```
Certificate:
  Subject: CN=kafka-broker-1.example.com
  X509v3 Subject Alternative Name:
    DNS:kafka-broker-1.example.com
    DNS:kafka-broker-1
    DNS:*.kafka.example.com
    IP:192.168.1.10
```

**Connection attempts:**
```
Connect to kafka-broker-1.example.com ✓ (matches SAN)
Connect to kafka-broker-1 ✓ (matches SAN)
Connect to kafka-broker-2.kafka.example.com ✓ (matches wildcard)
Connect to 192.168.1.10 ✓ (matches IP SAN)
Connect to different-name.com ✗ (no match)
```

### When Hostname Verification Fails

**Common error:**
```
javax.net.ssl.SSLPeerUnverifiedException: Host name 'localhost' does not match the certificate subject provided by the peer (CN=kafka-broker-1.example.com)
```

**Causes:**
1. Certificate CN/SAN doesn't match hostname
2. Using IP address when cert only has hostname
3. Using hostname when cert only has IP
4. Certificate issued for different domain

**Solutions:**
1. Generate certificate with correct hostname/IP in SAN
2. Connect using hostname that matches certificate
3. For development only: disable verification (not recommended)

### Complete SSL Configuration Example

**Secure production setup:**

```properties
# Broker configuration
listeners=SSL://kafka-broker-1.example.com:9093
ssl.keystore.location=/var/private/ssl/kafka.server.keystore.jks
ssl.keystore.password=changeit
ssl.key.password=changeit
ssl.truststore.location=/var/private/ssl/kafka.server.truststore.jks
ssl.truststore.password=changeit
# ssl.endpoint.identification.algorithm defaults to "https" - no need to set
```

**Client configuration:**
```properties
bootstrap.servers=kafka-broker-1.example.com:9093
security.protocol=SSL
ssl.truststore.location=/path/to/client.truststore.jks
ssl.truststore.password=changeit
# ssl.endpoint.identification.algorithm defaults to "https" - hostname verification enabled
```

### Disabling for Development (Not Recommended)

**Only for local development:**

```properties
# CLIENT configuration (producer/consumer)
ssl.endpoint.identification.algorithm=

# Now you can use:
bootstrap.servers=localhost:9093
# Or:
bootstrap.servers=127.0.0.1:9093
# Even if certificate is for "kafka-broker.example.com"
```

**NEVER do this in production!**

### Inter-Broker Communication

**Broker-to-broker SSL:**

```properties
# Broker configuration
listeners=SSL://kafka-broker-1.example.com:9093
inter.broker.listener.name=SSL
ssl.endpoint.identification.algorithm=https  # Enabled for inter-broker too
```

**Each broker:**
- Validates other brokers' certificates
- Checks hostname matches
- Prevents rogue brokers from joining

### Testing Hostname Verification

**Test with OpenSSL:**

```bash
# Connect and check certificate
openssl s_client -connect kafka-broker-1.example.com:9093 -showcerts

# Look for:
# subject=CN=kafka-broker-1.example.com
# X509v3 Subject Alternative Name: DNS:kafka-broker-1.example.com
```

**Test with Kafka tools:**

```bash
# This should succeed (hostname matches)
kafka-broker-api-versions.sh --bootstrap-server kafka-broker-1.example.com:9093 \
  --command-config client-ssl.properties

# This might fail (IP doesn't match unless in SAN)
kafka-broker-api-versions.sh --bootstrap-server 192.168.1.10:9093 \
  --command-config client-ssl.properties
```

### Algorithm Options

**Supported values:**

1. **"https"** (default, recommended)
   - Standard HTTPS hostname verification
   - RFC 2818 compliance
   - Validates CN and SAN

2. **"" (empty string)**
   - Disables verification
   - Insecure
   - Development only

**No other values are valid**

### Monitoring SSL Issues

**Common log messages:**

**Success:**
```
[2025-12-12 10:00:00,123] INFO Successfully authenticated with kafka-broker-1.example.com
```

**Hostname mismatch:**
```
[2025-12-12 10:00:00,123] ERROR SSL handshake failed: Host name 'localhost' does not match the certificate subject
```

**Certificate not trusted:**
```
[2025-12-12 10:00:00,123] ERROR SSL handshake failed: unable to find valid certification path to requested target
```

### Best Practices

**Production deployment:**

1. **Always use hostname verification:**
   ```properties
   # Default is secure, no need to set
   # ssl.endpoint.identification.algorithm=https
   ```

2. **Generate proper certificates:**
   ```bash
   # Include all hostnames and IPs in SAN
   # CN=kafka-broker-1.example.com
   # SAN=kafka-broker-1.example.com,192.168.1.10
   ```

3. **Use DNS names in bootstrap.servers:**
   ```properties
   # Good
   bootstrap.servers=kafka-broker-1.example.com:9093

   # Bad (might not match certificate)
   bootstrap.servers=192.168.1.10:9093
   ```

4. **Test before deployment:**
   ```bash
   # Verify certificate details
   openssl x509 -in broker-cert.pem -text -noout
   ```

### Key Takeaway

**Remember:**
- `ssl.endpoint.identification.algorithm` **defaults to "https"** (secure)
- This enables hostname verification automatically
- Prevents man-in-the-middle attacks
- No manual configuration needed for secure defaults
- Empty string disables verification (dangerous, never use in production)
- Ensure certificates include proper CN/SAN for all hostnames

---

## Question 18 - Inter-Broker Listener Configuration

**Domain:** Cluster Configuration & Management
**Type:** Multiple-Choice

**Your Answer:** d) inter.broker.protocol.name
**Correct Answer:** a) inter.broker.listener.name

### Explanation

The correct configuration parameter to specify which listener brokers use for inter-broker communication is `inter.broker.listener.name`, not `inter.broker.protocol.name` (which doesn't exist).

### Understanding Kafka Listeners

**Listeners vs. Inter-Broker Communication**

Brokers can have multiple listeners for different purposes:

```properties
# Broker configuration
listeners=INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:9093,SSL://0.0.0.0:9094

# Which listener do brokers use to talk to each other?
inter.broker.listener.name=INTERNAL
```

### The Correct Configuration

**inter.broker.listener.name**

```properties
# Define multiple listeners
listeners=INTERNAL://kafka-broker-1:9092,EXTERNAL://public.kafka.com:9093

# Specify which listener for broker-to-broker communication
inter.broker.listener.name=INTERNAL

# Map listener names to security protocols
listener.security.protocol.map=INTERNAL:PLAINTEXT,EXTERNAL:SSL
```

**What this means:**
- Brokers communicate with each other using the INTERNAL listener
- INTERNAL uses PLAINTEXT protocol (internal network, no encryption)
- Clients can use EXTERNAL listener (SSL encrypted, public network)

### Why Your Answer Was Wrong

**Your answer:** `inter.broker.protocol.name`

**Incorrect because:**
- This configuration parameter **does not exist** in Kafka
- It's a confusion of two real configurations:
  - `inter.broker.listener.name` (correct)
  - `security.inter.broker.protocol` (deprecated, different purpose)

**The confusion:**
```properties
# Real config (old, deprecated)
security.inter.broker.protocol=SSL

# Real config (current, correct)
inter.broker.listener.name=INTERNAL

# Fake config (does not exist)
inter.broker.protocol.name=???  # ✗ Not valid
```

### Related Configuration (Deprecated)

**security.inter.broker.protocol (deprecated)**

```properties
# Old way (deprecated in Kafka 1.0+)
security.inter.broker.protocol=SSL

# New way (recommended)
inter.broker.listener.name=INTERNAL
listener.security.protocol.map=INTERNAL:SSL
```

**Why deprecated:**
- Less flexible (can only specify protocol, not listener)
- Can't have different listeners for clients vs. brokers
- Replaced by listener.name approach

### Complete Multi-Listener Setup

**Scenario:** Separate internal and external access

**Broker configuration:**
```properties
# Broker 1
broker.id=1

# Define two listeners
listeners=INTERNAL://kafka-1.internal:9092,EXTERNAL://kafka-1.external.com:9093

# Advertise different addresses
advertised.listeners=INTERNAL://kafka-1.internal:9092,EXTERNAL://kafka-1.external.com:9093

# Map listener names to security protocols
listener.security.protocol.map=INTERNAL:PLAINTEXT,EXTERNAL:SSL

# Inter-broker uses INTERNAL listener
inter.broker.listener.name=INTERNAL
```

**Result:**
```
Brokers communicate:
  Broker 1 → Broker 2: kafka-2.internal:9092 (PLAINTEXT, fast)

Clients connect:
  External clients → kafka-1.external.com:9093 (SSL, secure)
  Internal clients → kafka-1.internal:9092 (PLAINTEXT, fast)
```

### Three-Listener Example (Internal, External, SSL)

```properties
# Broker configuration
listeners=INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:9093,CONTROLLER://0.0.0.0:9094

listener.security.protocol.map=INTERNAL:SASL_PLAINTEXT,EXTERNAL:SASL_SSL,CONTROLLER:PLAINTEXT

advertised.listeners=INTERNAL://kafka-1.private:9092,EXTERNAL://kafka-1.public.com:9093,CONTROLLER://kafka-1.controller:9094

# Brokers use CONTROLLER listener for replication
inter.broker.listener.name=CONTROLLER
```

**Use cases:**
- INTERNAL: Internal clients (SASL auth, no encryption)
- EXTERNAL: External clients (SASL + SSL)
- CONTROLLER: Broker-to-broker (no auth/encryption, isolated network)

### Why Separate Listeners Matter

**Without separation (single listener):**
```properties
listeners=EXTERNAL://0.0.0.0:9093
listener.security.protocol.map=EXTERNAL:SSL
inter.broker.listener.name=EXTERNAL
```

**Problem:**
- Broker-to-broker traffic encrypted (unnecessary overhead)
- All traffic goes through external network interface
- Performance degradation (SSL encryption for replication)
- Network routing inefficiency

**With separation (multiple listeners):**
```properties
listeners=INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:9093
listener.security.protocol.map=INTERNAL:PLAINTEXT,EXTERNAL:SSL
inter.broker.listener.name=INTERNAL
```

**Benefits:**
- Broker-to-broker: Fast PLAINTEXT on private network
- Client-to-broker: Secure SSL on public network
- Optimized performance
- Network segmentation

### Validation and Troubleshooting

**Check listener configuration:**

```bash
# See broker configuration
kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Check broker metadata
kafka-metadata.sh --snapshot /tmp/kafka-logs/__cluster_metadata-0/*.log --print
```

**Common errors:**

**Error 1: Listener name not defined**
```properties
inter.broker.listener.name=INTERNAL
listeners=EXTERNAL://0.0.0.0:9093  # INTERNAL not defined!
```

```
ERROR Broker failed to start: Listener INTERNAL not found in listeners list
```

**Error 2: Security protocol not mapped**
```properties
inter.broker.listener.name=INTERNAL
listeners=INTERNAL://0.0.0.0:9092
# Missing: listener.security.protocol.map=INTERNAL:PLAINTEXT
```

```
ERROR Security protocol not found for listener INTERNAL
```

**Error 3: Wrong listener name**
```properties
inter.broker.listener.name=INTERNAL
listeners=CONTROLLER://0.0.0.0:9092  # Name mismatch
```

```
ERROR Configured inter.broker.listener.name INTERNAL not found
```

### KRaft Mode Considerations

**In KRaft mode (no ZooKeeper):**

```properties
# KRaft requires separate controller listener
listeners=INTERNAL://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093

listener.security.protocol.map=INTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT

# Inter-broker communication
inter.broker.listener.name=INTERNAL

# Controller communication (KRaft-specific)
controller.listener.names=CONTROLLER
```

**Key differences:**
- `controller.listener.names` for KRaft controller quorum
- `inter.broker.listener.name` for data replication
- Two separate communication channels

### Performance Impact

**Benchmark: SSL vs. PLAINTEXT for inter-broker**

```
Configuration 1 (SSL for everything):
  inter.broker.listener.name=EXTERNAL (SSL)
  Replication throughput: 200 MB/s
  CPU usage: 60%

Configuration 2 (PLAINTEXT for inter-broker):
  inter.broker.listener.name=INTERNAL (PLAINTEXT)
  Replication throughput: 800 MB/s
  CPU usage: 15%

Performance gain: 4x throughput, 75% less CPU
```

**Why the difference:**
- SSL encryption overhead eliminated for replication
- More CPU available for client requests
- Faster recovery from failures

### Security Considerations

**Is PLAINTEXT secure for inter-broker?**

**Yes, if:**
- Brokers are on isolated private network
- Network is trusted (VPC, private VLAN)
- Physical/network security controls in place

**No, if:**
- Brokers on public network
- Shared network with untrusted hosts
- Compliance requires encryption in transit

**Best practice:**
```properties
# Internal network: PLAINTEXT (performance)
inter.broker.listener.name=INTERNAL
listener.security.protocol.map=INTERNAL:PLAINTEXT

# External clients: SSL (security)
listener.security.protocol.map=EXTERNAL:SSL
```

### Migration from Old to New Config

**Old configuration (deprecated):**
```properties
security.inter.broker.protocol=SSL
```

**New configuration (recommended):**
```properties
listeners=INTERNAL://0.0.0.0:9092
listener.security.protocol.map=INTERNAL:SSL
inter.broker.listener.name=INTERNAL
```

**Migration steps:**
1. Add new listener configuration
2. Restart brokers with both old and new config
3. Verify brokers communicate correctly
4. Remove deprecated `security.inter.broker.protocol`
5. Rolling restart to finalize

### Key Takeaway

**Remember:**
- Use `inter.broker.listener.name` to specify inter-broker communication listener
- NOT `inter.broker.protocol.name` (doesn't exist)
- Separate listeners for internal (broker-to-broker) and external (client) traffic
- Map listener names to security protocols with `listener.security.protocol.map`
- Deprecated: `security.inter.broker.protocol`
- Performance benefit: PLAINTEXT for inter-broker on private network

---

## Question 42 - min.insync.replicas Default Value

**Domain:** Cluster Configuration & Management
**Type:** Multiple-Choice

**Your Answer:** a) The default value is 0
**Correct Answer:** b) The default value is 1

### Explanation

The `min.insync.replicas` configuration **defaults to 1**, not 0. This is an important default that affects durability guarantees when using `acks=all`.

### Understanding min.insync.replicas

**What it controls:**

When a producer sends messages with `acks=all`, the broker only acknowledges the write after it has been replicated to at least `min.insync.replicas` replicas that are in the ISR (In-Sync Replica set).

```properties
min.insync.replicas=1  # Default value
```

### Default Behavior (min.insync.replicas=1)

**Setup:**
```properties
# Topic configuration
replication.factor=3
min.insync.replicas=1  # Default

# Producer configuration
acks=all
```

**Write scenario:**
```
Topic: orders, Partition 0
Replicas: [Broker 1 (leader), Broker 2, Broker 3]
ISR: [1, 2, 3]

Producer sends message with acks=all:
1. Leader (Broker 1) writes message
2. Check: ISR size (3) >= min.insync.replicas (1) ✓
3. Leader acknowledges immediately (doesn't wait for followers)

Result: Message acknowledged after leader write only
```

### Why Your Answer Was Wrong

**Your answer:** "The default value is 0"

**Incorrect because:**
- `min.insync.replicas=0` would be meaningless
- It would mean "no replicas needed" - contradicts the whole point
- Kafka defaults to `1` for basic durability
- A value of 0 would provide no guarantees even with `acks=all`

**What would min.insync.replicas=0 mean?**
```
Hypothetically:
- No replicas required to be in sync
- acks=all would be useless
- No durability guarantee
- Defeats the purpose of replication

This is why it's not the default (or even allowed in practice)
```

### Typical Production Configuration

**Recommended setup for durability:**

```properties
# Topic configuration
replication.factor=3
min.insync.replicas=2  # NOT the default 1!

# Producer configuration
acks=all
```

**Why min.insync.replicas=2:**
```
Scenario: Leader fails after write but before replication

With min.insync.replicas=1 (default):
- Leader writes and ACKs immediately
- Leader crashes before followers replicate
- Message lost ✗

With min.insync.replicas=2:
- Leader writes
- At least 1 follower must replicate
- Then leader ACKs
- Leader crashes
- Follower has the message ✓
```

### Configuration Levels

**Broker default (applies to all topics):**
```properties
# server.properties
min.insync.replicas=1  # Default if not set
```

**Topic-specific override:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name critical-data \
  --alter \
  --add-config min.insync.replicas=2
```

**Check current value:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name my-topic \
  --describe

# Output:
# Configs for topic 'my-topic' are:
#   min.insync.replicas=2
```

### Interaction with acks Setting

**Producer acks=all with different min.insync.replicas:**

| acks | min.insync.replicas | ISR | Result |
|------|-------------------|-----|--------|
| all | 1 (default) | [1,2,3] | ACK after leader write |
| all | 2 | [1,2,3] | ACK after leader + 1 follower |
| all | 2 | [1,2] | ACK after leader + 1 follower |
| all | 2 | [1] | NOT_ENOUGH_REPLICAS error |
| all | 3 | [1,2,3] | ACK after all 3 replicas |
| all | 3 | [1,2] | NOT_ENOUGH_REPLICAS error |

**Key insight:**
```
Required: ISR.size >= min.insync.replicas

If not met: Producer gets NOT_ENOUGH_REPLICAS_AFTER_APPEND error
```

### Default vs. Recommended Values

**Kafka defaults (focused on availability):**
```properties
replication.factor=1  # Default
min.insync.replicas=1  # Default
```
- Low durability
- High availability
- Acceptable for development
- **NOT recommended for production**

**Production recommendations (focused on durability):**
```properties
replication.factor=3  # Recommended
min.insync.replicas=2  # Recommended
```
- High durability (can lose 1 broker)
- Balanced availability
- Industry best practice

### Common Mistake: Default is Unsafe

**Development setup (uses defaults):**
```properties
# Topic created with defaults
replication.factor=1
min.insync.replicas=1

# Producer
acks=all  # Developer thinks this makes it durable
```

**Problem:**
```
acks=all + min.insync.replicas=1 + replication.factor=1
= Message acknowledged after single broker write
= No replication durability
= False sense of security!
```

**Correct production setup:**
```properties
# Topic
replication.factor=3
min.insync.replicas=2

# Producer
acks=all

= Message acknowledged after 2 brokers write
= Can survive 1 broker failure
= True durability ✓
```

### Error Scenarios

**Scenario 1: ISR shrinks below min.insync.replicas**

```
Initial state:
  Topic: payments
  Replication factor: 3
  min.insync.replicas: 2
  ISR: [1, 2, 3]

Broker 2 crashes:
  ISR: [1, 3]  (still >= 2) ✓
  Writes continue

Broker 3 also crashes:
  ISR: [1]  (< 2) ✗
  Producer error: NOT_ENOUGH_REPLICAS_AFTER_APPEND
```

**Error handling:**
```java
try {
    producer.send(record).get();
} catch (ExecutionException e) {
    if (e.getCause() instanceof NotEnoughReplicasException) {
        // ISR.size < min.insync.replicas
        // Options:
        // 1. Retry (wait for brokers to recover)
        // 2. Alert operations team
        // 3. Fail gracefully
    }
}
```

**Scenario 2: Topic creation with constraints**

```bash
# Try to create topic
kafka-topics.sh --create \
  --topic my-topic \
  --replication-factor 2 \
  --config min.insync.replicas=3 \
  --bootstrap-server localhost:9092

# ERROR: min.insync.replicas cannot be greater than replication.factor
```

**Valid configurations:**
```
replication.factor >= min.insync.replicas

Valid:
  RF=3, min.insync=2 ✓
  RF=3, min.insync=1 ✓
  RF=2, min.insync=2 ✓

Invalid:
  RF=2, min.insync=3 ✗
  RF=1, min.insync=2 ✗
```

### Monitoring min.insync.replicas Violations

**JMX metric:**
```
kafka.server:type=ReplicaManager,name=UnderMinIsrPartitionCount

Value > 0: Some partitions have ISR < min.insync.replicas
Action: Alert! Writes failing for affected partitions
```

**Check via CLI:**
```bash
kafka-topics.sh --describe \
  --topic my-topic \
  --under-min-isr-partitions \
  --bootstrap-server localhost:9092

# Lists partitions where ISR < min.insync.replicas
```

### Tuning Recommendations

**Low-latency, non-critical data:**
```properties
replication.factor=2
min.insync.replicas=1  # Default, fast writes
```

**Balanced (most production workloads):**
```properties
replication.factor=3
min.insync.replicas=2  # Standard production setting
```

**Maximum durability (financial, critical):**
```properties
replication.factor=3
min.insync.replicas=3  # All replicas must ACK (slowest)
```

**Trade-off:**
```
Higher min.insync.replicas:
  + Better durability
  - Higher latency
  - Lower availability (more failure scenarios cause writes to fail)

Lower min.insync.replicas:
  - Lower durability
  + Lower latency
  + Higher availability
```

### Key Takeaway

**Remember:**
- `min.insync.replicas` **defaults to 1**, not 0
- Default provides minimal durability (leader only)
- Production recommendation: Set to 2 with RF=3
- Works with `acks=all` to ensure replication before ACK
- Must satisfy: ISR.size >= min.insync.replicas
- Invalid: min.insync.replicas > replication.factor
- Monitor UnderMinIsrPartitionCount metric

---

## Question 43 - Consumer Offset Retention Parameter

**Domain:** Cluster Configuration & Management
**Type:** Multiple-Choice

**Your Answer:** a) consumer.offset.retention.ms
**Correct Answer:** b) offsets.retention.minutes

### Explanation

The correct configuration parameter for controlling how long consumer offsets are retained is `offsets.retention.minutes`, not `consumer.offset.retention.ms`.

### The Correct Parameter

**offsets.retention.minutes**

```properties
# Broker configuration (server.properties)
offsets.retention.minutes=10080  # 7 days (default)
```

**What it does:**
- Controls how long Kafka retains committed consumer offsets
- After this period, inactive consumer group offsets are deleted
- Applies when a consumer group becomes empty (no active consumers)

### Why Your Answer Was Wrong

**Your answer:** `consumer.offset.retention.ms`

**Incorrect because:**
- This parameter **does not exist** in Kafka configuration
- It combines naming patterns from different configs incorrectly
- The actual parameter is `offsets.retention.minutes` (note: minutes, not ms)

**Common confusion:**
```properties
# Real parameter (correct)
offsets.retention.minutes=10080

# Fake parameter (does not exist)
consumer.offset.retention.ms=604800000  # ✗ Not valid

# Another real parameter (different purpose)
offsets.commit.timeout.ms=5000  # Offset commit timeout
```

### Offset Retention Behavior

**Timeline with offsets.retention.minutes=10080 (7 days):**

```
Day 0: Consumer group "my-group" actively consuming
       Offsets committed: partition-0: offset 1000

Day 1: Consumer group stops (all consumers leave)
       Group becomes empty
       Retention timer starts

Day 8: 7 days elapsed since group became empty
       Offsets for "my-group" are deleted

Day 9: New consumer joins "my-group"
       No offset found
       Starts from beginning (auto.offset.reset=earliest)
       or end (auto.offset.reset=latest)
```

### Units: Minutes, Not Milliseconds

**Important detail:**

Most Kafka time configurations use milliseconds:
```properties
session.timeout.ms=45000
request.timeout.ms=30000
auto.commit.interval.ms=5000
```

**But offset retention uses MINUTES:**
```properties
offsets.retention.minutes=10080  # MINUTES, not ms!
```

**Conversion:**
```
Default: 10080 minutes
= 10080 / 60 hours
= 168 hours
= 7 days
```

### Common Configurations

**Default (7 days):**
```properties
offsets.retention.minutes=10080
```
- Suitable for most use cases
- Allows weekly restarts without offset loss

**Short retention (1 day):**
```properties
offsets.retention.minutes=1440
```
- For temporary consumer groups
- Faster cleanup of inactive offsets

**Long retention (30 days):**
```properties
offsets.retention.minutes=43200
```
- For infrequent consumers
- Monthly batch jobs
- Greater safety margin

**Unlimited retention:**
```properties
offsets.retention.minutes=-1
```
- Offsets never deleted
- Requires manual cleanup
- Can grow __consumer_offsets topic indefinitely

### When Offsets Are Deleted

**Retention timer starts when:**
1. Consumer group becomes **empty** (no active members)
2. Group coordinator confirms all consumers left
3. Timer counts from last commit timestamp

**Important:** Active consumer groups never have offsets deleted, regardless of retention setting!

**Example:**
```
Group: "processor-app"
offsets.retention.minutes: 1440 (1 day)

Scenario 1: Consumer actively running for 30 days
  Result: Offsets retained ✓ (group is active)

Scenario 2: Consumer stops for 2 days
  Result: Offsets deleted ✗ (exceeded 1 day retention)

Scenario 3: Consumer runs daily for 1 hour
  Result: Offsets retained ✓ (never inactive > 1 day)
```

### Checking Current Configuration

**Via kafka-configs.sh:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type brokers \
  --entity-default \
  --describe

# Look for:
# offsets.retention.minutes=10080
```

**Via broker logs:**
```bash
grep "offsets.retention.minutes" /var/log/kafka/server.log
```

**Via JMX/metrics:**
```
# This is a static config, check broker properties file:
cat /etc/kafka/server.properties | grep offsets.retention.minutes
```

### Impact on Consumer Recovery

**Scenario: Consumer downtime exceeds retention**

```
Initial state:
  Group: "analytics-job"
  Last offset: 5000
  Last activity: Day 0
  offsets.retention.minutes: 1440 (1 day)

Day 2: Consumer restarts (downtime > 1 day)
  Offset check: NOT FOUND (deleted)
  Fallback: auto.offset.reset config

With auto.offset.reset=earliest:
  Consumer starts from beginning (offset 0)
  Processes all historical data (potential duplicate processing)

With auto.offset.reset=latest:
  Consumer starts from current end
  Misses all messages during downtime (data loss)
```

### Best Practices

**Set retention based on maintenance windows:**

**Daily deployments:**
```properties
offsets.retention.minutes=2880  # 2 days
# Allows 1 day of downtime + buffer
```

**Weekly batch jobs:**
```properties
offsets.retention.minutes=20160  # 14 days
# Allows job to skip a week if needed
```

**Monthly jobs:**
```properties
offsets.retention.minutes=43200  # 30 days
```

**Critical applications:**
```properties
offsets.retention.minutes=-1  # Never delete
# But monitor __consumer_offsets growth
```

### Related Configurations

**Consumer-side offset management:**

```properties
# How often consumer auto-commits (if enabled)
auto.commit.interval.ms=5000

# Timeout for manual offset commit
request.timeout.ms=30000

# What to do when no offset found
auto.offset.reset=latest  # or earliest
```

**Broker-side offset topic:**

```properties
# Retention of offset topic itself (log retention)
offsets.retention.minutes=10080  # When to delete offset entries

# Offset topic partitions
offsets.topic.num.partitions=50

# Offset topic replication
offsets.topic.replication.factor=3
```

### __consumer_offsets Topic

**Where offsets are stored:**

```bash
# View offset topic
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic __consumer_offsets \
  --formatter "kafka.coordinator.group.GroupMetadataManager\$OffsetsMessageFormatter"

# Output (example):
# [my-group,my-topic,0]::OffsetAndMetadata(offset=1000, ...)
```

**Cleanup happens automatically:**
- Kafka log cleaner compacts __consumer_offsets
- Deletes entries older than offsets.retention.minutes
- Only for empty/inactive consumer groups

### Troubleshooting Offset Loss

**Problem:** Consumer resets to beginning unexpectedly

**Check 1: Offset retention**
```bash
# Is retention too short?
grep offsets.retention.minutes /etc/kafka/server.properties

# Has group been inactive too long?
kafka-consumer-groups.sh --describe --group my-group --bootstrap-server localhost:9092
```

**Check 2: Consumer group state**
```bash
kafka-consumer-groups.sh --describe --group my-group --bootstrap-server localhost:9092

# STATE column:
#   Empty = offsets subject to retention cleanup
#   Stable = offsets retained indefinitely
```

**Fix: Increase retention**
```properties
# Before: 1 day retention
offsets.retention.minutes=1440

# After: 7 days retention
offsets.retention.minutes=10080
```

### Migration Considerations

**Changing retention on live cluster:**

```bash
# 1. Check current value
kafka-configs.sh --describe --entity-type brokers --entity-default --bootstrap-server localhost:9092

# 2. Change dynamically (no restart needed)
kafka-configs.sh --alter --entity-type brokers --entity-default \
  --add-config offsets.retention.minutes=20160 \
  --bootstrap-server localhost:9092

# 3. Verify change
kafka-configs.sh --describe --entity-type brokers --entity-default --bootstrap-server localhost:9092
```

**Note:** This is a **dynamic configuration** - no broker restart required!

### Key Takeaway

**Remember:**
- Parameter name is `offsets.retention.minutes` (NOT consumer.offset.retention.ms)
- Uses **minutes**, not milliseconds (unusual for Kafka configs)
- Default: 10080 minutes (7 days)
- Applies when consumer group becomes empty/inactive
- Active groups retain offsets regardless of this setting
- Can be changed dynamically without broker restart
- Set based on maximum acceptable downtime for your consumers

---

## Question 46 - BytesInPerSec Metric Matching

**Domain:** Monitoring and Observability
**Type:** Matching

**Your Answer:** d (matched BytesInPerSec with "Number of times ISR shrinks")
**Correct Answer:** b (BytesInPerSec should match "Total rate of producer data sent to broker")

### Explanation

The `BytesInPerSec` metric measures the **rate of incoming data (bytes per second)** from producers to the broker, not ISR shrink events. You incorrectly matched it with option "d" which describes the `IsrShrinksPerSec` metric.

### Understanding BytesInPerSec

**Full JMX metric path:**
```
kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec
```

**What it measures:**
- Total bytes per second received by the broker
- Incoming data from producers
- Aggregate across all topics (or per-topic)
- Key metric for understanding write throughput

### Correct Matching

**BytesInPerSec → "Total rate of producer data sent to broker"**

**Example values:**
```
BytesInPerSec: 10485760  (10 MB/s incoming data)
BytesInPerSec: 52428800  (50 MB/s incoming data)
BytesInPerSec: 104857600 (100 MB/s incoming data)
```

**What this tells you:**
- How much data producers are sending
- Network ingress load
- Disk write load (before compression)
- Scaling needs for broker capacity

### Why Your Answer Was Wrong

**Your answer:** Matched BytesInPerSec with "Number of times ISR shrinks"

**Why incorrect:**
- ISR shrink events are counted by `IsrShrinksPerSec`, not BytesInPerSec
- BytesInPerSec measures data volume (bytes), not events (count)
- Completely different metric type and purpose

**The metric you should have matched to "ISR shrinks":**
```
kafka.server:type=ReplicaManager,name=IsrShrinksPerSec

Description: Rate of ISR shrink events (replicas falling out of sync)
```

### BytesInPerSec Variants

**Broker-level (aggregate):**
```
kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec

Measures: Total bytes/sec across all topics on this broker
```

**Topic-level:**
```
kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec,topic=orders

Measures: Bytes/sec for specific topic "orders"
```

**Per-partition (via other metrics):**
```
# Calculate from log segment growth
```

### Related Metrics (Common Matching Exam Questions)

**Incoming data (producer → broker):**
```
BytesInPerSec: Bytes received from producers
MessagesInPerSec: Messages received from producers
```

**Outgoing data (broker → consumer):**
```
BytesOutPerSec: Bytes sent to consumers
```

**Request metrics:**
```
TotalProduceRequestsPerSec: Number of produce requests
TotalFetchRequestsPerSec: Number of fetch requests
```

**Replication metrics:**
```
IsrShrinksPerSec: Rate of ISR shrink events
IsrExpandsPerSec: Rate of ISR expand events
UnderReplicatedPartitions: Count of under-replicated partitions
```

### Complete Metric Matching Reference

| Metric | Measures | Typical Values |
|--------|----------|----------------|
| **BytesInPerSec** | Producer data rate (bytes) | 10 MB/s, 100 MB/s |
| **BytesOutPerSec** | Consumer data rate (bytes) | 50 MB/s, 200 MB/s |
| **MessagesInPerSec** | Producer message count rate | 1000/s, 10000/s |
| **IsrShrinksPerSec** | ISR shrink event rate | 0 (healthy), >0 (problems) |
| **IsrExpandsPerSec** | ISR expand event rate | Low rate normal |
| **UnderReplicatedPartitions** | Partitions with ISR < RF | 0 (healthy), >0 (replication lag) |
| **OfflinePartitionsCount** | Partitions without leader | 0 (healthy), >0 (critical) |
| **RequestsPerSec** | Total request rate | Varies widely |

### Monitoring BytesInPerSec

**Via JMX:**
```bash
# Using jmxterm or similar
get -b kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec OneMinuteRate

# Output:
# OneMinuteRate = 10485760.5  (10 MB/s)
```

**Via Prometheus (with JMX Exporter):**
```yaml
# JMX Exporter config
rules:
  - pattern: 'kafka.server<type=BrokerTopicMetrics, name=BytesInPerSec><>Count'
    name: kafka_server_bytes_in_total

  - pattern: 'kafka.server<type=BrokerTopicMetrics, name=BytesInPerSec><>OneMinuteRate'
    name: kafka_server_bytes_in_rate
```

**Query in Prometheus:**
```promql
# Current rate
rate(kafka_server_bytes_in_total[5m])

# Per-topic
rate(kafka_server_bytes_in_total{topic="orders"}[5m])
```

**Via Grafana dashboard:**
```
Graph: Bytes In Rate
Query: rate(kafka_server_bytes_in_total[5m])
Unit: bytes/sec
```

### Alert Thresholds

**High BytesInPerSec:**
```yaml
# Alert if ingress exceeds capacity
- alert: HighIngressRate
  expr: kafka_server_bytes_in_rate > 100000000  # 100 MB/s
  annotations:
    summary: "Broker receiving excessive data"
    description: "Broker {{ $labels.instance }} receiving {{ $value }} bytes/s"
```

**Low BytesInPerSec (unexpected):**
```yaml
# Alert if usually-busy topic goes quiet
- alert: LowIngressRate
  expr: kafka_server_bytes_in_rate{topic="critical-data"} < 1000000  # 1 MB/s
  for: 5m
  annotations:
    summary: "Critical topic ingress dropped"
```

### Troubleshooting with BytesInPerSec

**Scenario 1: BytesInPerSec = 0 (no data incoming)**

**Possible causes:**
- Producers stopped/crashed
- Network connectivity issues
- Authentication/authorization failures
- Topic doesn't exist

**Investigation:**
```bash
# Check producer errors
# Check network connectivity
# Check broker logs for rejected requests
grep "WARN" /var/log/kafka/server.log | grep -i "produce"
```

**Scenario 2: BytesInPerSec very high (unexpected spike)**

**Possible causes:**
- Batch job started
- Replay of historical data
- Producer retry storm
- Attack/abuse

**Investigation:**
```bash
# Check per-topic breakdown
# Identify which topic/client is responsible
kafka-broker-api-versions.sh --bootstrap-server localhost:9092
```

### BytesInPerSec vs. Disk Write Rate

**Important distinction:**

```
BytesInPerSec (metric) ≠ Disk write rate

Why:
1. Compression: Data compressed before disk write
2. Batching: Multiple messages batched into segments
3. Page cache: May be in memory, not yet flushed to disk
4. Replication: Leader counts BytesIn, followers don't
```

**Example:**
```
BytesInPerSec: 100 MB/s  (uncompressed from producers)
Compression ratio: 5x
Disk write rate: 20 MB/s  (compressed)
```

### Complete Monitoring Dashboard

**Essential metrics to monitor together:**

```
Throughput:
- BytesInPerSec: Producer ingress
- BytesOutPerSec: Consumer egress
- MessagesInPerSec: Message rate

Health:
- UnderReplicatedPartitions: Replication lag
- OfflinePartitionsCount: Partition outages
- IsrShrinksPerSec: ISR instability

Performance:
- RequestHandlerAvgIdlePercent: Broker capacity
- NetworkProcessorAvgIdlePercent: Network threads
- RequestQueueSize: Backlog
```

### Key Takeaway

**Remember:**
- `BytesInPerSec` measures **producer data rate (bytes/sec)** sent to broker
- NOT ISR shrink rate (that's `IsrShrinksPerSec`)
- Available at broker-level and topic-level
- Critical metric for capacity planning
- Combine with BytesOutPerSec for complete throughput picture
- Monitor to detect ingress anomalies and scaling needs

**Common exam matching:**
- BytesInPerSec → Producer data rate ✓
- BytesOutPerSec → Consumer data rate ✓
- IsrShrinksPerSec → ISR shrink events ✓
- UnderReplicatedPartitions → Replication lag ✓

---

## Question 53 - NOT_ENOUGH_REPLICAS Resolution

**Domain:** Troubleshooting
**Type:** Multiple-Response

**Your Answer:** b, c, d (Increase replication factor, ensure replicas in ISR, set acks=0)
**Correct Answer:** b, c (Increase replication factor, ensure replicas in ISR)

### Explanation

The `NOT_ENOUGH_REPLICAS` error occurs when producing with `acks=all` but the ISR size is less than `min.insync.replicas`. The correct solutions are to fix the underlying replication issue (option b, c), **NOT** to set `acks=0` which just masks the problem and risks data loss.

### Understanding NOT_ENOUGH_REPLICAS

**Error scenario:**

```properties
# Topic configuration
replication.factor=3
min.insync.replicas=2

# Current state
ISR: [1]  # Only 1 replica in sync

# Producer configuration
acks=all

# Producer sends message
Result: NOT_ENOUGH_REPLICAS_AFTER_APPEND exception
```

**Why the error occurs:**
```
Producer requires: ISR.size >= min.insync.replicas
Current state: ISR.size (1) < min.insync.replicas (2)
Result: Write rejected
```

### Correct Solutions

**Option b) Increase the topic's replication factor ✓**

**When to use:** Topic has insufficient replicas

```bash
# Current state
Topic: orders
Replication factor: 2
ISR: [1]  (1 of 2 replicas)
min.insync.replicas: 2

# Problem: Even if all replicas sync, ISR.size = 2 (barely enough)
# If one fails, ISR.size = 1 (NOT_ENOUGH_REPLICAS)

# Solution: Increase replication factor
kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --reassignment-json-file increase-rf.json \
  --execute

# increase-rf.json
{
  "version": 1,
  "partitions": [
    {
      "topic": "orders",
      "partition": 0,
      "replicas": [1, 2, 3],  # Added replica on broker 3
      "log_dirs": ["any", "any", "any"]
    }
  ]
}

# New state
Replication factor: 3
ISR: [1, 2, 3]
Result: ISR.size (3) >= min.insync.replicas (2) ✓
```

**Why this works:**
- More replicas = higher chance of meeting min.insync.replicas
- Better fault tolerance
- Reduces likelihood of ISR shrinking below threshold

**Option c) Ensure that all followers are in the ISR ✓**

**When to use:** Replicas exist but are out of sync

```bash
# Current state
Topic: payments
Replication factor: 3
Replicas: [1, 2, 3]
ISR: [1]  # Followers 2, 3 are out of sync!
min.insync.replicas: 2

# Problem: Followers can't keep up
# Causes:
# 1. Slow disk I/O on followers
# 2. Network issues
# 3. Under-resourced brokers
# 4. Broker failures

# Solution: Fix follower lag issues

# 1. Check why followers are lagging
kafka-topics.sh --describe --topic payments --bootstrap-server localhost:9092

# Output:
# Topic: payments  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1
# (Replicas 2, 3 are lagging)

# 2. Investigate broker health
# Check disk I/O
iostat -x 1

# Check broker logs
grep "Replica.*fell behind" /var/log/kafka/server.log

# 3. Fix underlying issues
# - Restart failed brokers
# - Provision more disk I/O capacity
# - Fix network issues
# - Increase replica.lag.time.max.ms if needed (temporary)

# 4. Verify followers catch up
kafka-topics.sh --describe --topic payments --bootstrap-server localhost:9092

# Output after fix:
# Topic: payments  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2,3 ✓
```

**Why this works:**
- Fixes the root cause (replication lag)
- Restores ISR to full size
- Enables writes to succeed
- Maintains durability guarantees

### Why Option d is WRONG

**Option d) Set producer acks=0 to bypass the check ✗**

**Why this is INCORRECT:**

**What acks=0 does:**
```properties
# Producer configuration
acks=0
```

**Behavior:**
- Producer sends message, doesn't wait for ANY acknowledgment
- No confirmation that message was received
- No confirmation that message was written to disk
- **Highest risk of data loss**

**Why this is a terrible solution:**

```
Before (with acks=all):
  Producer → Broker: Write message
  Broker: ISR.size < min.insync.replicas
  Broker → Producer: NOT_ENOUGH_REPLICAS error
  Producer: Knows write failed, can retry
  Result: No data loss ✓

After (with acks=0):
  Producer → Broker: Write message
  Producer: Immediately considers send successful (no wait)
  Broker: Might fail to write (disk full, crash, ISR issue)
  Producer: Never knows about failure
  Result: Silent data loss ✗
```

**Analogy:**
```
Problem: Your smoke detector keeps alarming (real fire)
Option D solution: Remove batteries from smoke detector
Result: No more alarm, but house still burning!

acks=0 doesn't fix the problem, it just hides it!
```

### Proper acks Configuration

**acks=0 (no acknowledgment):**
```properties
acks=0
# Use case: Metrics, logs where loss is acceptable
# Durability: Lowest (data loss likely)
# Performance: Highest (no waiting)
```

**acks=1 (leader only):**
```properties
acks=1
# Use case: Balanced workloads
# Durability: Medium (leader failure = data loss)
# Performance: Medium
```

**acks=all/-1 (all in-sync replicas):**
```properties
acks=all
# Use case: Critical data (financial, user data)
# Durability: Highest (no data loss if min.insync.replicas >= 2)
# Performance: Lowest (waits for replication)
```

**NEVER change from acks=all to acks=0 to "fix" NOT_ENOUGH_REPLICAS!**

### Complete Resolution Steps

**Step-by-step troubleshooting:**

**1. Diagnose the issue**
```bash
# Check topic configuration
kafka-topics.sh --describe --topic my-topic --bootstrap-server localhost:9092

# Output example:
# Topic: my-topic  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1
#                                                              ^^^
#                                      ISR only has 1 replica (problem!)

# Check min.insync.replicas
kafka-configs.sh --describe --entity-type topics --entity-name my-topic --bootstrap-server localhost:9092

# Output:
# min.insync.replicas=2
```

**2. Identify root cause**
```bash
# Check broker health
kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Check replication lag
kafka-topics.sh --describe --under-replicated-partitions --bootstrap-server localhost:9092

# Check broker logs
tail -f /var/log/kafka/server.log | grep -i "replica"
```

**3. Apply appropriate fix**

**If brokers are down:**
```bash
# Restart failed brokers
systemctl start kafka

# Verify they rejoin ISR
watch "kafka-topics.sh --describe --topic my-topic --bootstrap-server localhost:9092"
```

**If followers are lagging:**
```bash
# Check and fix resource issues
# - Disk I/O bottleneck
# - Network issues
# - Insufficient CPU/memory

# Temporary: Increase lag tolerance (use with caution)
kafka-configs.sh --alter --entity-type brokers --entity-name 2 \
  --add-config replica.lag.time.max.ms=30000 \
  --bootstrap-server localhost:9092
```

**If replication factor too low:**
```bash
# Increase replication factor (as shown in option b)
kafka-reassign-partitions.sh --execute --reassignment-json-file rf-increase.json --bootstrap-server localhost:9092
```

**4. Verify resolution**
```bash
# Check ISR is healthy
kafka-topics.sh --describe --topic my-topic --bootstrap-server localhost:9092

# Test producer
kafka-console-producer.sh --topic my-topic --bootstrap-server localhost:9092
> test message
> ^C

# Should succeed without NOT_ENOUGH_REPLICAS error
```

### Monitoring to Prevent NOT_ENOUGH_REPLICAS

**JMX metrics to watch:**

```
# Partitions under min ISR
kafka.server:type=ReplicaManager,name=UnderMinIsrPartitionCount

# Alert if > 0
# Indicates partitions where writes will fail

# ISR shrink rate
kafka.server:type=ReplicaManager,name=IsrShrinksPerSec

# Alert if consistently > 0
# Indicates replication stability issues
```

**Alerting configuration:**
```yaml
# Prometheus alert
- alert: UnderMinISRPartitions
  expr: kafka_server_replica_manager_under_min_isr_partition_count > 0
  for: 5m
  annotations:
    summary: "Kafka partitions under min ISR"
    description: "{{ $value }} partitions cannot accept writes (acks=all)"
```

### Key Takeaway

**Remember:**
- NOT_ENOUGH_REPLICAS = ISR.size < min.insync.replicas
- **Correct fixes:** Increase replication factor (b), fix ISR lag (c)
- **WRONG fix:** Set acks=0 (d) - this masks the problem and risks data loss
- Never sacrifice durability to avoid error messages
- Fix root cause, don't hide symptoms
- Monitor UnderMinIsrPartitionCount metric
- Ensure RF >= min.insync.replicas + 1 for fault tolerance

**The exam wants you to understand:**
- acks=0 is NOT a solution, it's giving up on durability
- Real solutions address the underlying replication health issue

---

## Question 58 - Preferred Replica Election Tool

**Domain:** Troubleshooting
**Type:** Multiple-Choice

**Your Answer:** c) kafka-preferred-replica-election.sh
**Correct Answer:** b) kafka-leader-election.sh --election-type preferred

### Explanation

In modern Kafka (0.11+), the `kafka-preferred-replica-election.sh` tool has been **deprecated** and replaced by `kafka-leader-election.sh` with the `--election-type preferred` option.

### The Modern Tool

**kafka-leader-election.sh (current, recommended)**

```bash
# Trigger preferred replica election
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type preferred \
  --all-topic-partitions

# Or for specific topic
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type preferred \
  --topic my-topic \
  --partition 0
```

### Why Your Answer Was Wrong

**Your answer:** `kafka-preferred-replica-election.sh`

**Why incorrect:**
- This tool is **deprecated** since Kafka 0.11
- Still exists in some distributions for backward compatibility
- Modern Kafka documentation recommends `kafka-leader-election.sh`
- Uses old ZooKeeper-based approach (not compatible with KRaft)

**The deprecation:**
```bash
# Old (deprecated)
kafka-preferred-replica-election.sh --zookeeper localhost:2181

# Output:
# WARNING: This tool is deprecated, use kafka-leader-election.sh instead
```

### What is Preferred Replica Election?

**Concept:**

When you create a topic, Kafka assigns replicas in order:

```bash
kafka-topics.sh --create \
  --topic orders \
  --partitions 3 \
  --replication-factor 3 \
  --bootstrap-server localhost:9092

# Partition 0: Replicas [1, 2, 3]  ← Broker 1 is preferred leader
# Partition 1: Replicas [2, 3, 1]  ← Broker 2 is preferred leader
# Partition 2: Replicas [3, 1, 2]  ← Broker 3 is preferred leader
```

**Preferred leader = First replica in the list**

**Why preferred leaders matter:**
- Evenly distributes leadership
- Balances load across brokers
- Optimal for cluster performance

### When Preferred Leaders Get Out of Sync

**Scenario: Broker failure and recovery**

```
Initial state:
  Partition 0: Replicas [1, 2, 3]  Leader: 1 (preferred) ✓

Broker 1 crashes:
  Partition 0: Replicas [1, 2, 3]  Leader: 2 (failover) ✗
                                          ^^^ Not preferred

Broker 1 recovers:
  Partition 0: Replicas [1, 2, 3]  Leader: 2 (still) ✗
                                          ^^^ Should be 1!

  Kafka does NOT automatically rebalance leadership!
```

**Result: Unbalanced cluster**
```
Broker 1: Leader for 10 partitions (light load)
Broker 2: Leader for 50 partitions (heavy load)
Broker 3: Leader for 10 partitions (light load)
```

### Using kafka-leader-election.sh

**Election types:**

**1. Preferred replica election:**
```bash
# Rebalance all partitions to preferred leaders
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type preferred \
  --all-topic-partitions

# Output:
# Successfully completed leader election for partitions: orders-0, orders-1, ...
```

**2. Unclean leader election:**
```bash
# Allow out-of-sync replica to become leader (data loss risk)
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type unclean \
  --topic critical-topic \
  --partition 0

# WARNING: This may cause data loss!
# Only use for disaster recovery when partition is offline
```

### Complete Examples

**Example 1: Rebalance all topics after maintenance**

```bash
# After rolling restart, rebalance leadership
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type preferred \
  --all-topic-partitions

# This moves leaders back to preferred replicas
# Balances load across brokers
```

**Example 2: Rebalance specific topic**

```bash
# Rebalance just the "orders" topic
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type preferred \
  --topic orders

# Faster than all-topic-partitions
# Use when only one topic is imbalanced
```

**Example 3: Rebalance single partition**

```bash
# Very targeted - one partition only
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type preferred \
  --topic orders \
  --partition 3

# Use for testing or specific partition issues
```

### Automatic Preferred Replica Election

**Enable automatic rebalancing:**

```properties
# Broker configuration (Kafka 2.4+)
auto.leader.rebalance.enable=true

# How often to check for imbalance
leader.imbalance.check.interval.seconds=300  # 5 minutes

# Threshold to trigger rebalance
leader.imbalance.per.broker.percentage=10  # 10% imbalance
```

**How it works:**
```
Every 5 minutes:
1. Controller checks leader distribution
2. If any broker has >10% imbalance (compared to preferred)
3. Automatically triggers preferred replica election
4. Rebalances leadership
```

**Trade-off:**
- **Pros:** Automatic, keeps cluster balanced
- **Cons:** Causes brief unavailability during leadership change

**Production recommendation:**
```properties
# Disable auto-rebalance (default is true)
auto.leader.rebalance.enable=false

# Manually trigger during maintenance windows
# More control, less disruption
```

### Checking Leader Imbalance

**Before election:**
```bash
kafka-topics.sh --describe --topic orders --bootstrap-server localhost:9092

# Output:
# Partition: 0  Leader: 2  Replicas: 1,2,3  Isr: 1,2,3
# Partition: 1  Leader: 2  Replicas: 2,3,1  Isr: 1,2,3
# Partition: 2  Leader: 2  Replicas: 3,1,2  Isr: 1,2,3
#
# Problem: Broker 2 is leader for ALL partitions (imbalanced)
#          First replica (preferred) should be leader
```

**After preferred replica election:**
```bash
kafka-leader-election.sh \
  --bootstrap-server localhost:9092 \
  --election-type preferred \
  --topic orders

kafka-topics.sh --describe --topic orders --bootstrap-server localhost:9092

# Output:
# Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2,3 ✓
# Partition: 1  Leader: 2  Replicas: 2,3,1  Isr: 1,2,3 ✓
# Partition: 2  Leader: 3  Replicas: 3,1,2  Isr: 1,2,3 ✓
#
# Fixed: Each partition's leader matches first replica (preferred)
```

### ZooKeeper vs. Bootstrap Server

**Old tool (ZooKeeper-based):**
```bash
# Deprecated approach
kafka-preferred-replica-election.sh --zookeeper localhost:2181

# Problems:
# - Requires ZooKeeper access
# - Not compatible with KRaft
# - Deprecated
```

**New tool (Bootstrap server):**
```bash
# Modern approach
kafka-leader-election.sh --bootstrap-server localhost:9092

# Benefits:
# - No ZooKeeper access needed
# - Works with KRaft mode
# - Standard admin client API
```

### Monitoring Leader Distribution

**Check imbalance via JMX:**
```
kafka.controller:type=KafkaController,name=PreferredReplicaImbalanceCount

Value: Number of partitions not led by preferred replica
Goal: 0 (all partitions have preferred leader)
```

**CLI check:**
```bash
# Custom script to check imbalance
for topic in $(kafka-topics.sh --list --bootstrap-server localhost:9092); do
  kafka-topics.sh --describe --topic $topic --bootstrap-server localhost:9092 | \
  awk '{if ($4 != $6) print "Imbalanced: " $0}'
done

# Shows partitions where Leader != first replica
```

### When to Run Preferred Replica Election

**Good times:**
1. After broker maintenance/restart
2. After rolling cluster upgrade
3. After failure recovery
4. During planned maintenance window
5. When monitoring shows high imbalance

**Bad times:**
1. During high traffic periods
2. While cluster is unstable
3. During rebalancing already in progress
4. When ISR is unhealthy

### Impact of Leadership Change

**Brief unavailability during election:**
```
Timeline:
00:00 - Election triggered
00:01 - Old leader stops serving (NOT_LEADER_OR_FOLLOWER errors)
00:02 - New leader takes over
00:03 - Clients refresh metadata
00:04 - Normal operation resumes

Total impact: ~3-5 seconds of errors per partition
```

**Client handling:**
```java
// Clients should retry on NOT_LEADER_OR_FOLLOWER
props.put("retries", 3);
props.put("retry.backoff.ms", 100);

// Metadata refresh
props.put("metadata.max.age.ms", 5000);
```

### Key Takeaway

**Remember:**
- Modern tool: `kafka-leader-election.sh --election-type preferred`
- Deprecated tool: `kafka-preferred-replica-election.sh` (don't use)
- Rebalances leadership to first replica in replica list
- Run after broker failures/restarts to optimize load distribution
- Use `--all-topic-partitions` for cluster-wide rebalancing
- Automatic rebalancing available but not recommended for production
- Brief unavailability during leadership transition

**Exam tip:**
- If you see `kafka-preferred-replica-election.sh` → it's the old/deprecated tool
- Correct answer is always `kafka-leader-election.sh` with proper flags

---

## Final Summary

You've completed detailed explanations for all 14 incorrect answers from Exam 6. Here's a quick reference of the key takeaways:

### Quick Reference

1. **Auto-commit** - Timing based on interval, not continuous
2. **Zero-copy** - Direct disk-to-network transfer, disabled with SSL
3. **Consumer join** - Rebalance triggered BY JoinGroup, not after SyncGroup
4. **Null keys** - Round-robin/sticky partitioning, NOT partition 0
5. **Empty ISR** - Physical failures, NOT config settings
6. **fetch.max.wait.ms** - Wait for min.bytes, NOT offset commit timeout
7. **ACL setup** - Enable authorizer FIRST, then create ACLs
8. **SSL endpoint** - Defaults to "https" (secure), not empty string
9. **Inter-broker listener** - Use `inter.broker.listener.name` parameter
10. **min.insync.replicas** - Defaults to 1, NOT 0
11. **Offset retention** - Parameter is `offsets.retention.minutes` (minutes!)
12. **BytesInPerSec** - Producer data rate, NOT ISR shrinks
13. **NOT_ENOUGH_REPLICAS** - Fix replication, DON'T use acks=0
14. **Leader election** - Use `kafka-leader-election.sh`, deprecated tool is old

**Your exam performance: 46/60 (76.67%) - PASSED**

Great job on passing the advanced exam! These detailed explanations should help reinforce the concepts you missed and prepare you for the actual CCAAK certification.
