# lock.io v2 - Raft Distributed Lock Service
A distributed lock service implementing Google chubby's architecture using Raft consensus. Built for learning distributed system fundamentals.

## Why This Project?

This isn't just another lock service. I built this to deeply understand:
- **Raft consensus** - leader election, log replication, safety
- **Session-based coordination** - how Chubby/Zookeeper prevent zombie locks
- **Fence tokens** - preventing split-brain and delayed operations
- **Production patterns** - same architecture as etcd, Consul, Chubby

### Design Decisions & Tradeoffs

**Why session-based locking?**
- Traditional locks fail when clients crash
- Sessions + heartbeats = automatic cleanup
- Same pattern as Chubby (Google), Zookeeper (Apache)

**Why fence tokens?**
- Prevents delayed operations after leader change
- Critical for consistency in distributed systems

## Features

✅ **No single point of failure** - survives 1 out of 3 nodes failing  
✅ **Automatic failover** - new leader elected in ~5 seconds  
✅ **Linearizable consistency** - Raft provides strong guarantees  
✅ **Session management** - automatic lock cleanup on client failure  
✅ **Fence tokens** - prevents split-brain scenarios 
