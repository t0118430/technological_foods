# GitHub Issues - Ready to Import
**Project**: Technological Foods - Scalability Refactoring
**Total Issues**: 12 (4 epics + 8 user stories)

---
---

## EPIC ISSUES

---

### Issue #1: [EPIC] Async Infrastructure Foundation
**Labels**: `epic`, `P0-critical`, `architecture`, `performance`
**Milestone**: Sprint 1
**Effort**: 5 days

#### Description
Replace synchronous blocking architecture with async framework to support 50+ concurrent sensors and sub-200ms response times.

**Business Value**:
- Support 50+ sensors (currently maxes out at 10)
- Reduce response times from 2-5 seconds to <200ms
- Enable horizontal scaling

**Current Issues**:
- `BaseHTTPRequestHandler` blocks on every I/O operation
- No connection pooling = database serialization
- InfluxDB writes block entire request handler

**Target Architecture**:
- FastAPI with async/await
- PostgreSQL connection pooling (5-20 connections)
- Async batch InfluxDB writer
- Rate limiting for DDoS protection

#### User Stories
- [ ] #2: Migrate to FastAPI Framework
- [ ] #3: Implement Connection Pooling
- [ ] #4: Implement Rate Limiting
- [ ] #5: Implement Async InfluxDB Batch Writer

#### Success Metrics
- [ ] 50 concurrent POST requests complete in <200ms
- [ ] 100 concurrent GET requests complete in <50ms
- [ ] Zero connection timeouts under sustained load
- [ ] Rate limiting blocks >120 req/min

#### Dependencies
None - foundational work

---

### Issue #2: [EPIC] Background Processing & Queuing
**Labels**: `epic`, `P0-critical`, `architecture`, `reliability`
**Milestone**: Sprint 2
**Effort**: 5 days

#### Description
Implement distributed task queue to decouple long-running operations from API responses, enabling 100x faster response times and reliable notification delivery.

**Business Value**:
- API responses return immediately (accept-and-process pattern)
- Notification failures don't block sensor data ingestion
- Retry logic for failed operations
- Scale notification processing independently

**Current Issues**:
- Notifications sent synchronously in request handler (10-30s blocking)
- Rule evaluation blocks response (100-500ms)
- AC control creates event loop per request (inefficient)
- No retry mechanism for failures

**Target Architecture**:
- Celery task queue with Redis broker
- Background workers for notifications, rules, AC control
- Dead letter queue for permanent failures
- Exponential backoff retry logic

#### User Stories
- [ ] #6: Setup Celery Task Queue
- [ ] #7: Migrate Notifications to Background Tasks
- [ ] #8: Migrate Rule Engine to Background Tasks

#### Success Metrics
- [ ] POST `/api/data` returns in <50ms
- [ ] Notification delivery rate >99%
- [ ] Failed tasks retry automatically
- [ ] Workers process 100+ tasks/second

#### Dependencies
- #1: Async Infrastructure Foundation (FastAPI, Redis)

---

### Issue #3: [EPIC] Database Optimization
**Labels**: `epic`, `P1-high`, `database`, `performance`
**Milestone**: Sprint 2
**Effort**: 3 days

#### Description
Optimize database schema and queries to support millions of records with sub-100ms query times.

**Business Value**:
- Queries remain fast as data grows to millions of records
- Support complex analytics without performance degradation
- Reduce database server costs (fewer resources needed)

**Current Issues**:
- Missing indexes on time-based columns = full table scans
- N+1 queries in growth stage manager (100 crops = 101 queries)
- No composite indexes for common filter combinations
- SQLite serializes all concurrent access

**Target Architecture**:
- PostgreSQL with comprehensive indexing strategy
- Batch SQL operations (CTEs, bulk inserts)
- Partial indexes for active records only
- Query optimization for common patterns

#### User Stories
- [ ] #9: Add Comprehensive Database Indexes
- [ ] #10: Fix N+1 Query Problems

#### Success Metrics
- [ ] All queries use indexes (EXPLAIN shows no table scans)
- [ ] `/api/data/query` <100ms for 1M records
- [ ] Growth stage advancement: 100 crops in <100ms
- [ ] Database CPU usage <30% under load

#### Dependencies
- #3: Connection Pooling (PostgreSQL migration)

---

### Issue #4: [EPIC] Production Hardening
**Labels**: `epic`, `P2-medium`, `operations`, `monitoring`, `security`
**Milestone**: Sprint 3
**Effort**: 2 days

#### Description
Enterprise-grade monitoring, security, and operational tooling for 99.9% uptime SLA.

**Business Value**:
- Proactive issue detection before customers impacted
- Meet enterprise SLA requirements
- Automated maintenance reduces operational costs
- Security compliance for sensitive data

**Current Issues**:
- No metrics or monitoring
- No alerting for system issues
- Data retention not executing (unbounded growth)
- Weak security (plaintext API keys, exposed errors)

**Target Architecture**:
- Prometheus metrics + Grafana dashboards
- Automated data retention with configurable policies
- Security hardening (API key hashing, input validation)
- Load balancing for high availability

#### User Stories
- [ ] #11: Implement Application Monitoring
- [ ] #12: Implement Data Retention Automation

#### Success Metrics
- [ ] Prometheus metrics showing 99.9% uptime
- [ ] Alerts trigger before customer impact
- [ ] Data automatically cleaned per retention policy
- [ ] Security audit passes

#### Dependencies
- All previous epics (foundation must be stable)

---
---

## USER STORY ISSUES

---

### Issue #5: Migrate to FastAPI Framework
**Labels**: `P0-critical`, `enhancement`, `backend`, `story-points-8`
**Epic**: #1 - Async Infrastructure Foundation
**Milestone**: Sprint 1
**Assignee**: Backend Engineer
**Effort**: 1 day (8 story points)

#### User Story
**As a** DevOps engineer
**I want** the API server to use an async framework
**So that** multiple sensor requests can be handled concurrently without blocking

#### Current Problem
- `BaseHTTPRequestHandler` is single-threaded and synchronous
- Every I/O operation blocks the request handler
- 10 concurrent requests = 10+ second total response time
- No built-in API documentation

#### Proposed Solution
- Migrate to FastAPI with async/await
- Auto-generated OpenAPI documentation
- Built-in request validation with Pydantic
- Native CORS support

#### Acceptance Criteria
- [ ] FastAPI application replaces `BaseHTTPRequestHandler`
- [ ] All existing endpoints migrated to FastAPI routes
- [ ] API documentation auto-generated at `/docs`
- [ ] Response times for `/api/data` endpoint <100ms (no external calls)
- [ ] Backward compatibility maintained for all clients
- [ ] Unit tests pass for all endpoints
- [ ] Load test: 50 concurrent requests complete successfully

#### Technical Tasks
- [ ] Setup FastAPI project structure (`app/main.py`, `app/routers/`, `app/models.py`)
- [ ] Migrate authentication middleware (API key validation)
- [ ] Migrate `/api/data` POST endpoint
- [ ] Migrate remaining endpoints (GET /latest, /query, /ac/control, etc.)
- [ ] Update startup script & systemd service
- [ ] Configure uvicorn with 4 workers
- [ ] Add CORS middleware
- [ ] Update integration tests

#### Code Example
```python
from fastapi import FastAPI, Depends, Header
from pydantic import BaseModel

app = FastAPI(title="Technological Foods IoT API")

class SensorReading(BaseModel):
    sensor_type: str
    value: float

@app.post("/api/data", status_code=202)
async def post_sensor_data(
    reading: SensorReading,
    api_key: str = Depends(verify_api_key)
):
    # Process asynchronously
    return {"status": "accepted"}
```

#### Dependencies
None - foundational change

#### Risks & Mitigation
- **Risk**: Breaking changes for existing clients
  - **Mitigation**: Maintain exact response format, comprehensive testing
- **Risk**: Learning curve for async programming
  - **Mitigation**: Code reviews, pair programming

---

### Issue #6: Implement Connection Pooling
**Labels**: `P0-critical`, `enhancement`, `database`, `story-points-13`
**Epic**: #1 - Async Infrastructure Foundation
**Milestone**: Sprint 1
**Assignee**: Backend Engineer
**Effort**: 1.5 days (13 story points)

#### User Story
**As a** backend developer
**I want** database connections to be pooled
**So that** concurrent requests don't serialize on database access

#### Current Problem
- SQLite opens/closes connection for each operation
- All concurrent access serializes (SQLite limitation)
- No connection reuse between requests
- Will deadlock at >20 concurrent clients

#### Proposed Solution
- Migrate to PostgreSQL with connection pooling
- SQLAlchemy ORM with QueuePool
- Min 5 connections, max 20 connections
- Alembic for schema migrations

#### Acceptance Criteria
- [ ] PostgreSQL replaces SQLite as primary database
- [ ] Connection pool configured with min=5, max=20 connections
- [ ] 50 concurrent queries complete in <500ms total
- [ ] No connection leaks after 1000 requests
- [ ] All existing data migrated from SQLite
- [ ] Schema migrations automated with Alembic

#### Technical Tasks
- [ ] Install and configure PostgreSQL 14+
- [ ] Create database and app user
- [ ] Configure PostgreSQL for performance (shared_buffers, max_connections)
- [ ] Install SQLAlchemy, psycopg2, alembic
- [ ] Implement connection pool with QueuePool
- [ ] Create SQLAlchemy ORM models
- [ ] Setup Alembic for migrations
- [ ] Create initial migration (schema)
- [ ] Migrate data from SQLite to PostgreSQL
- [ ] Update all database access to use SQLAlchemy
- [ ] Remove old SQLite code
- [ ] Update tests to use PostgreSQL

#### Code Example
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost/hydroponics",
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=15,
    pool_pre_ping=True
)
```

#### Dependencies
- #5: FastAPI migration (for dependency injection)

#### Risks & Mitigation
- **Risk**: Data loss during migration
  - **Mitigation**: Backup SQLite, verify row counts match, run in staging first
- **Risk**: PostgreSQL config issues
  - **Mitigation**: Use production-ready config template, load test

---

### Issue #7: Implement Rate Limiting
**Labels**: `P0-critical`, `security`, `enhancement`, `story-points-5`
**Epic**: #1 - Async Infrastructure Foundation
**Milestone**: Sprint 1
**Assignee**: Backend Engineer
**Effort**: 0.5 days (5 story points)

#### User Story
**As a** system administrator
**I want** API endpoints to enforce rate limits
**So that** the system is protected from abuse and DDoS attacks

#### Current Problem
- No rate limiting on any endpoint
- One client can DOS entire system
- No protection from misbehaving sensors
- Vulnerable to resource exhaustion

#### Proposed Solution
- SlowAPI middleware with Redis backend
- 120 req/min per API key (2/second average)
- 60 req/min per IP for public endpoints
- Custom rate limit headers in responses

#### Acceptance Criteria
- [ ] Rate limiting enforced on all POST endpoints
- [ ] Limit: 120 requests/minute per API key (2 req/sec average)
- [ ] Limit: 60 requests/minute per IP address (for public endpoints)
- [ ] Rate limit headers included in responses (`X-RateLimit-*`)
- [ ] 429 status returned when limit exceeded
- [ ] Retry-After header indicates when to retry

#### Technical Tasks
- [ ] Install slowapi and redis packages
- [ ] Configure Redis connection for rate limiting
- [ ] Initialize Limiter with Redis backend
- [ ] Add SlowAPIMiddleware to FastAPI app
- [ ] Apply rate limits to POST /api/data (120/min)
- [ ] Apply rate limits to POST /api/ac/control (60/min)
- [ ] Apply rate limits to POST /api/clients (10/min)
- [ ] Apply rate limits to GET /api/data/query (300/min)
- [ ] Add custom rate limit key function (by API key)
- [ ] Test rate limit enforcement
- [ ] Document rate limits in API docs

#### Code Example
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)

@app.post("/api/data")
@limiter.limit("120/minute")
async def post_sensor_data(...):
    pass
```

#### Dependencies
- #5: FastAPI migration
- Redis installed (for #6 or standalone)

#### Risks & Mitigation
- **Risk**: Legitimate users hit rate limit
  - **Mitigation**: Set generous limits (2/sec = 7200/hour), monitor usage
- **Risk**: Redis failure = no rate limiting
  - **Mitigation**: Fail-open strategy, Redis high availability

---

### Issue #8: Implement Async InfluxDB Batch Writer
**Labels**: `P0-critical`, `enhancement`, `performance`, `story-points-3`
**Epic**: #1 - Async Infrastructure Foundation
**Milestone**: Sprint 1
**Assignee**: Backend Engineer
**Effort**: 0.5 days (3 story points)

#### User Story
**As a** backend developer
**I want** InfluxDB writes to be batched and asynchronous
**So that** sensor data ingestion doesn't block API responses

#### Current Problem
- InfluxDB writes use SYNCHRONOUS mode
- Every sensor reading = blocking HTTP call to InfluxDB (100-500ms)
- 10 sensors = 10 blocking writes = 5+ seconds
- No batching or buffering

#### Proposed Solution
- Use InfluxDB async batch writer
- Buffer up to 500 points or 10 seconds
- Retry failed writes with exponential backoff
- Graceful shutdown flushes pending writes

#### Acceptance Criteria
- [ ] InfluxDB writes use async batch API
- [ ] Batch size: 500 points or 10 seconds (whichever comes first)
- [ ] POST `/api/data` returns in <50ms (before InfluxDB write)
- [ ] Failed writes retry 3 times with exponential backoff
- [ ] Write success rate monitored (>99.9%)

#### Technical Tasks
- [ ] Configure WriteOptions for batching (batch_size=500, flush_interval=10s)
- [ ] Set up retry configuration (max_retries=3, exponential backoff)
- [ ] Implement success callback (logging)
- [ ] Implement error callback (dead letter queue)
- [ ] Implement retry callback (monitoring)
- [ ] Add graceful shutdown handler (flush pending writes)
- [ ] Add SIGTERM/SIGINT signal handlers
- [ ] Test write batching under load
- [ ] Verify no data loss during shutdown

#### Code Example
```python
from influxdb_client.client.write_api import WriteOptions

write_options = WriteOptions(
    batch_size=500,
    flush_interval=10_000,
    max_retries=3,
    retry_interval=5_000
)

write_api = influx_client.write_api(write_options=write_options)
write_api.write(bucket=BUCKET, record=point)  # Non-blocking!
```

#### Dependencies
- #5: FastAPI migration (async support)

#### Risks & Mitigation
- **Risk**: Data loss if server crashes before flush
  - **Mitigation**: Graceful shutdown handlers, small flush interval (10s max)
- **Risk**: InfluxDB downtime causes buffer overflow
  - **Mitigation**: Dead letter queue for failed writes

---

### Issue #9: Setup Celery Task Queue
**Labels**: `P0-critical`, `enhancement`, `architecture`, `story-points-8`
**Epic**: #2 - Background Processing & Queuing
**Milestone**: Sprint 2
**Assignee**: Backend Engineer
**Effort**: 1 day (8 story points)

#### User Story
**As a** backend developer
**I want** a distributed task queue for background jobs
**So that** notifications, rule evaluation, and AC control don't block API responses

#### Current Problem
- All processing happens synchronously in request handler
- Notifications block for 10-30 seconds
- No retry mechanism for failures
- Can't scale processing independently

#### Proposed Solution
- Celery distributed task queue
- Redis broker for task distribution
- 2 worker processes (scalable)
- Flower monitoring dashboard

#### Acceptance Criteria
- [ ] Celery configured with Redis broker
- [ ] 2 worker processes running
- [ ] Tasks can be queued and executed asynchronously
- [ ] Failed tasks retry with exponential backoff
- [ ] Flower monitoring dashboard accessible
- [ ] Task execution time <5 seconds for notifications

#### Technical Tasks
- [ ] Install celery[redis] and flower packages
- [ ] Create celery_app.py with configuration
- [ ] Configure task serialization (JSON), timezone (UTC)
- [ ] Set task time limits (5 min hard, 4 min soft)
- [ ] Create tasks/ directory with __init__.py
- [ ] Auto-discover tasks from app.tasks module
- [ ] Create systemd service for celery workers
- [ ] Configure 2 worker processes with concurrency=2
- [ ] Create systemd service for Flower monitoring
- [ ] Configure NGINX reverse proxy for Flower
- [ ] Add basic auth to Flower dashboard
- [ ] Test task queuing and execution
- [ ] Verify retry logic works

#### Code Example
```python
from celery import Celery

celery_app = Celery(
    'hydroponics',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@celery_app.task(max_retries=3)
def send_notification_task(subject, body):
    # Async task execution
    pass
```

#### Dependencies
- #6: Connection Pooling (Redis installed)
- #5: FastAPI migration (for integration)

#### Risks & Mitigation
- **Risk**: Redis failure = task queue down
  - **Mitigation**: Redis persistence (AOF), consider Redis Sentinel for HA
- **Risk**: Workers crash and tasks are lost
  - **Mitigation**: Task acknowledgement settings, result backend

---

### Issue #10: Migrate Notifications to Background Tasks
**Labels**: `P0-critical`, `enhancement`, `reliability`, `story-points-8`
**Epic**: #2 - Background Processing & Queuing
**Milestone**: Sprint 2
**Assignee**: Backend Engineer
**Effort**: 1 day (8 story points)

#### User Story
**As a** system operator
**I want** notifications sent asynchronously
**So that** slow notification services don't block sensor data ingestion

#### Current Problem
- Notifications sent synchronously (blocking HTTP calls)
- Each notification channel = 10 second timeout
- 3 channels = 30 seconds blocked per alert
- Notification failures block entire request

#### Proposed Solution
- All notifications as Celery tasks
- Retry failed notifications (1min, 5min, 15min)
- Dead letter queue for permanent failures
- API returns immediately after queuing

#### Acceptance Criteria
- [ ] All notification sends are Celery tasks
- [ ] POST `/api/data` returns in <100ms even if notifications fail
- [ ] Failed notifications retry 3 times (1min, 5min, 15min delays)
- [ ] Notification delivery rate >99%
- [ ] Dead letter queue captures permanently failed notifications

#### Technical Tasks
- [ ] Create tasks/notifications.py with send_notification_task
- [ ] Configure task retry (max_retries=3, backoff=True)
- [ ] Implement task for each channel (ntfy, WhatsApp, email)
- [ ] Add error callbacks for logging failures
- [ ] Implement dead letter queue (failed_tasks table)
- [ ] Update POST /api/data to queue notifications instead of sending
- [ ] Remove synchronous notification calls from rule_engine.py
- [ ] Remove synchronous calls from alert_escalation.py
- [ ] Remove synchronous calls from drift_detection_service.py
- [ ] Create admin endpoint to view failed notifications
- [ ] Add manual retry endpoint for failed notifications
- [ ] Test notification delivery and retry logic

#### Code Example
```python
@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900
)
def send_notification_task(self, subject, body, channels):
    notifier = MultiChannelNotifier()
    notifier.send(subject, body, channels)
```

#### Dependencies
- #9: Celery setup

#### Risks & Mitigation
- **Risk**: Notifications delayed vs real-time
  - **Mitigation**: Workers process quickly (<1s), acceptable for alerts
- **Risk**: Lost notifications if worker crashes
  - **Mitigation**: Task acknowledgement, result backend, dead letter queue

---

### Issue #11: Add Comprehensive Database Indexes
**Labels**: `P1-high`, `enhancement`, `database`, `story-points-3`
**Epic**: #3 - Database Optimization
**Milestone**: Sprint 2
**Assignee**: Backend Engineer
**Effort**: 0.5 days (3 story points)

#### User Story
**As a** database administrator
**I want** indexes on all frequently queried columns
**So that** queries remain fast as data grows to millions of records

#### Current Problem
- Missing indexes on timestamp columns
- Range queries do full table scans
- No composite indexes for common filters
- Queries will slow exponentially with data growth

#### Proposed Solution
- Comprehensive indexing strategy
- Time-based indexes (DESC for recent-first)
- Composite indexes for common query patterns
- Partial indexes for active records only

#### Acceptance Criteria
- [ ] Indexes added for all time-based queries
- [ ] Composite indexes for common filter combinations
- [ ] Query execution plans show index usage (no table scans)
- [ ] `/api/data/query` response time <100ms for 1M records

#### Technical Tasks
- [ ] Create Alembic migration for indexes
- [ ] Add B-tree indexes on timestamp columns (events, harvests, calibrations, growth_stages)
- [ ] Add composite indexes (crops: status+variety, events: type+client+date)
- [ ] Add foreign key indexes (crops.client_id, harvests.crop_id, etc.)
- [ ] Add partial indexes for active records (WHERE status='active')
- [ ] Run migration with CONCURRENTLY option (no downtime)
- [ ] Verify indexes created (pg_indexes query)
- [ ] Run EXPLAIN ANALYZE on common queries
- [ ] Verify no table scans in query plans
- [ ] Monitor index size vs table size (<20%)

#### Code Example
```sql
-- Time-based index
CREATE INDEX idx_events_created_at ON events(created_at DESC);

-- Composite index
CREATE INDEX idx_crops_status_variety ON crops(status, variety_id);

-- Partial index
CREATE INDEX idx_crops_active ON crops(client_id, variety_id)
WHERE status = 'active';
```

#### Dependencies
- #6: PostgreSQL migration

#### Risks & Mitigation
- **Risk**: Index creation locks table
  - **Mitigation**: Use CREATE INDEX CONCURRENTLY (no locks)
- **Risk**: Indexes consume storage
  - **Mitigation**: Monitor index size, drop unused indexes

---

### Issue #12: Fix N+1 Query Problems
**Labels**: `P1-high`, `enhancement`, `performance`, `story-points-5`
**Epic**: #3 - Database Optimization
**Milestone**: Sprint 2
**Assignee**: Backend Engineer
**Effort**: 0.5 days (5 story points)

#### User Story
**As a** backend developer
**I want** database operations to use batch queries
**So that** hundreds of crops can be processed without hundreds of queries

#### Current Problem
- Growth stage advancement: 1 query per crop (100 crops = 101 queries)
- Client service checks: Loop through results in Python
- Calibration checks: Individual queries per sensor
- 5+ seconds for batch operations

#### Proposed Solution
- SQL CTEs (Common Table Expressions) for batch updates
- Single UPDATE query with WHERE IN clause
- Bulk insert operations
- Join-based queries instead of loops

#### Acceptance Criteria
- [ ] Growth stage advancement uses single batch query
- [ ] Client service checks use joins instead of loops
- [ ] Sensor calibration checks batched
- [ ] Maximum 3 queries for any batch operation (1 SELECT, 1 UPDATE, 1 INSERT)

#### Technical Tasks
- [ ] Refactor growth_stage_manager.check_and_advance_stages()
  - [ ] Use CTE to find completed stages
  - [ ] Single UPDATE to mark completed
  - [ ] Bulk INSERT for new stages
- [ ] Refactor client_manager.get_clients_needing_service()
  - [ ] Move date calculations to SQL (date_part)
  - [ ] Use LEFT JOIN instead of Python loop
- [ ] Refactor drift_detection_service batch checks
  - [ ] Query all sensors in single query
  - [ ] Batch comparison logic
- [ ] Add query logging to verify improvements
- [ ] Benchmark before/after (100 crops)
- [ ] Update tests for new query patterns

#### Code Example
```python
# BEFORE: N+1 queries
crops = db.get_active_crops()  # 1 query
for crop in crops:  # N iterations
    db.advance_stage(crop.id)  # N queries

# AFTER: 2 queries
query = """
WITH stages_to_complete AS (
    SELECT id FROM growth_stages
    WHERE status='active' AND days_elapsed >= days_duration
)
UPDATE growth_stages SET status='completed'
WHERE id IN (SELECT id FROM stages_to_complete)
RETURNING crop_id;
"""
db.execute(query)  # 1 query
db.bulk_insert_stages(new_stages)  # 1 query
```

#### Dependencies
- #6: PostgreSQL migration
- #11: Database indexes (for performance)

#### Risks & Mitigation
- **Risk**: Complex SQL harder to maintain
  - **Mitigation**: Add comments, unit tests for query logic
- **Risk**: Breaking existing functionality
  - **Mitigation**: Comprehensive test coverage, staging deployment

---

---

## QUICK START GUIDE

### Option 1: Create Issues with GitHub CLI
```bash
# Create epic
gh issue create --title "[EPIC] Async Infrastructure Foundation" \
  --body-file epic_1.md \
  --label "epic,P0-critical,architecture" \
  --milestone "Sprint 1"

# Create user story
gh issue create --title "Migrate to FastAPI Framework" \
  --body-file story_5.md \
  --label "P0-critical,enhancement,story-points-8" \
  --milestone "Sprint 1"
```

### Option 2: Copy to GitHub Web UI
1. Go to: https://github.com/t0118430/technological_foods/issues/new
2. Copy title and description from above
3. Add labels manually
4. Assign to milestone
5. Submit

### Labels to Create (if not exists)
```bash
# Priority labels
gh label create "P0-critical" --color "d93f0b" --description "Must fix immediately"
gh label create "P1-high" --color "ff6b6b" --description "Important, fix soon"
gh label create "P2-medium" --color "ffa500" --description "Should fix"

# Type labels
gh label create "epic" --color "3e4b9e" --description "Epic - collection of stories"

# Story point labels
gh label create "story-points-3" --color "c5def5"
gh label create "story-points-5" --color "c5def5"
gh label create "story-points-8" --color "c5def5"
gh label create "story-points-13" --color "c5def5"
```

### Milestones to Create
```bash
gh api repos/:owner/:repo/milestones -f title="Sprint 1" -f description="Week 1: Foundation"
gh api repos/:owner/:repo/milestones -f title="Sprint 2" -f description="Week 2: Async Processing"
gh api repos/:owner/:repo/milestones -f title="Sprint 3" -f description="Week 3: Production Hardening"
```

---

## TRACKING PROGRESS

### Sprint Board View
Use GitHub Projects with columns:
- 📋 **Backlog** - Not started
- 🏗️ **In Progress** - Currently working
- 👀 **In Review** - Awaiting code review
- ✅ **Done** - Completed

### Burndown Tracking
- **Sprint 1**: 29 points total
- **Sprint 2**: 29 points total
- **Sprint 3**: 21 points total

Track daily progress and adjust capacity if needed.

---

**Next Steps**:
1. Create GitHub labels and milestones
2. Import issues using CLI or web UI
3. Assign team members
4. Start Sprint 1!
