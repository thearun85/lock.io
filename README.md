# lock.io - Raft Distributed Lock Service
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

## Tech Stack

| Component | Choice | Purpose |
|-----------|--------|-------------------------------|
| Framework | Flask | API endpoints for client access |
| Raft | pysyncobj | Replicated state machines |
| Testing | pytest | Automated testing |
| Container | Docker + Compose | Local Testing |

## Quick demo
```
# Run 3-node cluster locally
docker compose up --build

# localhost:5000/1/2 - Will display the cluster dashboard
```

## Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Check the status of Lock service |
| POST | /sessions | Create a client session |
| GET | /sessions/<session_id> | Get the client session details |
| POST | /sessions/<session_id>/keepalive | Extend session lifetime |
| DELETE | /sessions/<session_id> | Delete a session and release all its locks |
| POST | /sessions/<session_id>/locks/<resource> | Acquire a lock on a resource |
| GET | /sessions/<session_id>/locks | Get all locks held by a session |
| DELETE | /sessions/<session_id>/locks/<resource> | Release a lock |
| POST | /admin/cleanup | Delete all expired sessions and release its locks |
| GET | /admin/stats | Get the lock service statistics |
| GET | /admin/locks/<resource> | Get the lock status on a resource |
| GET | /cluster/status | Get the status for the Raft cluster |

**Health check API:**

```bash
curl http://localhost:5000/health
```
Expected Output:
```json
{
  "is_leader": false,
  "is_ready": true,
  "leader": "lock-node-2:4322",
  "service": "lock.io",
  "status": "healthy",
  "timestamp": "2026-01-23T10:24:57.788813+00:00",
  "version": "0.1.0"
}
```

**Create a client session API:**

```bash
curl -X POST http://localhost:5000/sessions \
-H "Content-Type: application/json" \
-d '{"client_id": "test-client-1", "timeout":100}'
```
Expected Output:
```json
{
  "client_id": "test-client-1",
  "keepalive_interval": 33,
  "session_id": "02f55b83-8686-43fc-b54b-22aa06232543",
  "timeout": 100
}
```

**Get session info API:**

```bash
curl http://localhost:5000/sessions/02f55b83-8686-43fc-b54b-22aa06232543
```
Expected Output:
```json
{
  "client_id": "test-client-1",
  "created_at": 1769164036.1776488,
  "last_keepalive": 1769164036.1776495,
  "locks_held": [],
  "session_id": "02f55b83-8686-43fc-b54b-22aa06232543",
  "timeout": 100
}
```

**Keepalive API:**

```bash
curl -X POST http://localhost:5000/sessions/02f55b83-8686-43fc-b54b-22aa06232543/keepalive
```
Expected Output:
```json
{
  "session_id": "02f55b83-8686-43fc-b54b-22aa06232543",
  "success": true
}
```

**Delete client session API:**

```bash
curl -X DELETE http://localhost:5000/sessions/02f55b83-8686-43fc-b54b-22aa06232543
```
Expected Output:
```json
{
  "deleted": true,
  "session_id": "02f55b83-8686-43fc-b54b-22aa06232543"
}
```

**Acquire a lock on a resource API:**

```bash
curl -X POST http://localhost:5000/sessions/02f55b83-8686-43fc-b54b-22aa06232543/locks/resource-1
```
Expected Output:
```json
{
  "acquired": true,
  "fence_token": 1,
  "resource": "resource-1"
}
```

**Get all locks for a session API:**

```bash
curl http://localhost:5000/sessions/02f55b83-8686-43fc-b54b-22aa06232543/locks
```
Expected Output:
```json
{
  "locks": [
    "resource-1"
  ],
  "total_locks": 1
}
```

**Release a lock on a resource API:**

```bash
curl -X DELETE http://localhost:5000/sessions/02f55b83-8686-43fc-b54b-22aa06232543/locks/resource-1 -H "Content-Type: application/json" -d '{"fence_token": 1}'
```
Expected Output:
```json
{
  "released": true,
  "fence_token": 1,
  "resource": "resource-1"
}
```

**Admin stats API:**

```bash
curl http://localhost:5000/admin/stats
```
Expected Output:
```json
{
  "active_sessions": 2,
  "expired_sessions": 1,
  "fence_counter": 1,
  "total_locks": 1,
  "total_session": 3
}
```

**Admin cleanup of expired sessions API:**

```bash
curl -X POST http://localhost:5000/admin/cleanup
```
Expected Output:
```json
{
  "cleanup": "completed",
  "count": 1
}
```

**Admin - Lock status on a resource API:**

```bash
curl http://localhost:5000/admin/locks/resource-1
```
Expected Output:
```json
{
  "acquired_at": 1769166404.7297914,
  "fence_token": 1,
  "locked": true,
  "resource": "resource-1",
  "session_id": "02f55b83-8686-43fc-b54b-22aa06232543"
}
```
