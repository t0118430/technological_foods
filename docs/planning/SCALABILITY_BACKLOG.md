# 🎯 Scalability Implementation Backlog
**Project**: Technological Foods - Production Scalability
**Version**: 1.0
**Date**: 2026-02-09
**Timeline**: 3 weeks (15 working days)

---

## 📊 Epic Overview

| Epic ID | Epic Name | Business Value | Effort | Priority | Status |
|---------|-----------|----------------|--------|----------|--------|
| E1 | Async Infrastructure Foundation | Unblock scaling to 50+ sensors | 5 days | P0 | 🔴 Not Started |
| E2 | Background Processing & Queuing | Enable reliable notifications | 5 days | P0 | 🔴 Not Started |
| E3 | Database Optimization | 100x query performance | 3 days | P1 | 🔴 Not Started |
| E4 | Production Hardening | Enterprise SaaS readiness | 2 days | P2 | 🔴 Not Started |

**Total Estimated Effort**: 15 days (3 weeks, 1 engineer)

---

# EPIC 1: Async Infrastructure Foundation
**Goal**: Replace synchronous blocking architecture with async framework
**Business Value**: Support 50+ sensors with <200ms response times
**Timeline**: Week 1 (Days 1-5)

---

## User Story 1.1: Migrate to FastAPI Framework
**As a** DevOps engineer
**I want** the API server to use an async framework
**So that** multiple sensor requests can be handled concurrently without blocking

**Priority**: 🔴 P0 - CRITICAL
**Effort**: 8 story points (1 day)
**Dependencies**: None

### Acceptance Criteria
- [ ] FastAPI application replaces `BaseHTTPRequestHandler`
- [ ] All existing endpoints migrated to FastAPI routes
- [ ] API documentation auto-generated at `/docs`
- [ ] Response times for `/api/data` endpoint <100ms (no external calls)
- [ ] Backward compatibility maintained for all clients
- [ ] Unit tests pass for all endpoints
- [ ] Load test: 50 concurrent requests complete successfully

### Technical Tasks

#### Task 1.1.1: Setup FastAPI Project Structure
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Install dependencies:
   ```bash
   pip install fastapi[all] uvicorn[standard] pydantic python-multipart
   ```

2. Create new `backend/app/main.py`:
   ```python
   from fastapi import FastAPI, HTTPException, Depends, Header
   from fastapi.middleware.cors import CORSMiddleware
   from pydantic import BaseModel
   from typing import Optional
   import os

   app = FastAPI(
       title="Technological Foods IoT API",
       description="Enterprise Hydroponics Management System",
       version="2.0.0"
   )

   # CORS middleware
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Configure for production
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

   @app.get("/health")
   async def health_check():
       return {"status": "healthy", "version": "2.0.0"}
   ```

3. Create `backend/app/models.py` for Pydantic schemas
4. Create `backend/app/routers/` directory for endpoint modules
5. Update `requirements.txt`

**Deliverables**:
- ✅ FastAPI app starts on port 8000
- ✅ `/health` endpoint returns 200 OK
- ✅ API docs accessible at `http://localhost:8000/docs`

---

#### Task 1.1.2: Migrate Authentication Middleware
**Assignee**: Backend Engineer
**Effort**: 1 hour

**Steps**:
1. Create `backend/app/dependencies.py`:
   ```python
   from fastapi import Header, HTTPException, status
   import os

   async def verify_api_key(x_api_key: str = Header(None)):
       """Verify API key from header"""
       valid_key = os.getenv("API_KEY")
       if not x_api_key or x_api_key != valid_key:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Invalid or missing API key"
           )
       return x_api_key

   async def get_client_id(x_client_id: str = Header(None)):
       """Extract client ID from header"""
       if not x_client_id:
           raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST,
               detail="Missing X-Client-Id header"
           )
       return x_client_id
   ```

**Deliverables**:
- ✅ API key validation working
- ✅ Unauthorized requests return 401

---

#### Task 1.1.3: Migrate `/api/data` POST Endpoint
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Create `backend/app/routers/sensor_data.py`:
   ```python
   from fastapi import APIRouter, Depends, BackgroundTasks
   from pydantic import BaseModel, Field
   from typing import Optional, Literal
   from datetime import datetime
   from ..dependencies import verify_api_key, get_client_id

   router = APIRouter(prefix="/api/data", tags=["sensor_data"])

   class SensorReading(BaseModel):
       sensor_type: Literal["ph", "ec", "temperature", "water_level"]
       value: float = Field(..., ge=0, le=1000)
       timestamp: Optional[datetime] = None
       location: Optional[str] = None

   @router.post("", status_code=202)
   async def post_sensor_data(
       reading: SensorReading,
       background_tasks: BackgroundTasks,
       api_key: str = Depends(verify_api_key),
       client_id: str = Depends(get_client_id)
   ):
       """Ingest sensor data (async, non-blocking)"""
       # Add timestamp if not provided
       if not reading.timestamp:
           reading.timestamp = datetime.utcnow()

       # Write to InfluxDB asynchronously
       background_tasks.add_task(
           write_to_influx,
           client_id,
           reading.dict()
       )

       # Queue rule evaluation (doesn't block response)
       background_tasks.add_task(
           evaluate_rules,
           client_id,
           reading.dict()
       )

       return {
           "status": "accepted",
           "message": "Data queued for processing"
       }
   ```

2. Implement `write_to_influx()` helper
3. Implement `evaluate_rules()` helper

**Deliverables**:
- ✅ POST `/api/data` returns 202 Accepted in <50ms
- ✅ Data written to InfluxDB asynchronously
- ✅ Invalid data returns 422 with validation errors

---

#### Task 1.1.4: Migrate Remaining Endpoints
**Assignee**: Backend Engineer
**Effort**: 3 hours

**Endpoints to migrate**:
- `GET /api/data/latest`
- `GET /api/data/query`
- `POST /api/ac/control`
- `POST /api/ac/register`
- `GET /api/clients`
- `POST /api/clients`
- `GET /dashboard`

**Example** (`GET /api/data/latest`):
```python
from fastapi_cache.decorator import cache

@router.get("/latest")
@cache(expire=10)  # Cache for 10 seconds
async def get_latest_data(
    sensor_type: Optional[str] = None,
    client_id: str = Depends(get_client_id)
):
    """Get latest sensor readings (cached)"""
    result = await query_influx_latest(client_id, sensor_type)
    return {"data": result, "cached": True}
```

**Deliverables**:
- ✅ All endpoints migrated
- ✅ Backward compatible responses
- ✅ Integration tests pass

---

#### Task 1.1.5: Update Startup Script & Deployment
**Assignee**: DevOps Engineer
**Effort**: 1 hour

**Steps**:
1. Create `backend/start.sh`:
   ```bash
   #!/bin/bash
   # Production startup script
   uvicorn app.main:app \
       --host 0.0.0.0 \
       --port 8000 \
       --workers 4 \
       --log-level info \
       --access-log
   ```

2. Update systemd service:
   ```ini
   [Unit]
   Description=Technological Foods API
   After=network.target postgresql.service redis.service

   [Service]
   Type=notify
   User=app
   WorkingDirectory=/opt/hydroponics/backend
   Environment="PATH=/opt/hydroponics/venv/bin"
   ExecStart=/opt/hydroponics/backend/start.sh
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. Update Docker Compose:
   ```yaml
   services:
     api:
       build: ./backend
       command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=postgresql://user:pass@db:5432/hydroponics
         - REDIS_URL=redis://redis:6379/0
       depends_on:
         - db
         - redis
   ```

**Deliverables**:
- ✅ Service starts automatically on boot
- ✅ 4 worker processes running
- ✅ Logs to systemd journal

---

## User Story 1.2: Implement Connection Pooling
**As a** backend developer
**I want** database connections to be pooled
**So that** concurrent requests don't serialize on database access

**Priority**: 🔴 P0 - CRITICAL
**Effort**: 13 story points (1.5 days)
**Dependencies**: Task 1.1.1 (FastAPI setup)

### Acceptance Criteria
- [ ] PostgreSQL replaces SQLite as primary database
- [ ] Connection pool configured with min=5, max=20 connections
- [ ] 50 concurrent queries complete in <500ms total
- [ ] No connection leaks after 1000 requests
- [ ] All existing data migrated from SQLite
- [ ] Schema migrations automated with Alembic

### Technical Tasks

#### Task 1.2.1: Setup PostgreSQL Database
**Assignee**: DevOps Engineer
**Effort**: 2 hours

**Steps**:
1. Install PostgreSQL:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql-14 postgresql-contrib

   # Start service
   sudo systemctl enable postgresql
   sudo systemctl start postgresql
   ```

2. Create database and user:
   ```sql
   -- As postgres user
   CREATE DATABASE hydroponics;
   CREATE USER hydroponics_app WITH PASSWORD 'secure_password_here';
   GRANT ALL PRIVILEGES ON DATABASE hydroponics TO hydroponics_app;
   ```

3. Configure PostgreSQL for performance:
   ```bash
   # /etc/postgresql/14/main/postgresql.conf
   max_connections = 100
   shared_buffers = 256MB
   effective_cache_size = 1GB
   maintenance_work_mem = 64MB
   checkpoint_completion_target = 0.9
   wal_buffers = 16MB
   default_statistics_target = 100
   random_page_cost = 1.1
   effective_io_concurrency = 200
   work_mem = 2621kB
   min_wal_size = 1GB
   max_wal_size = 4GB
   ```

**Deliverables**:
- ✅ PostgreSQL 14+ running
- ✅ Database `hydroponics` created
- ✅ App user has correct permissions

---

#### Task 1.2.2: Implement Connection Pool with SQLAlchemy
**Assignee**: Backend Engineer
**Effort**: 3 hours

**Steps**:
1. Install dependencies:
   ```bash
   pip install sqlalchemy psycopg2-binary alembic
   ```

2. Create `backend/app/database.py`:
   ```python
   from sqlalchemy import create_engine
   from sqlalchemy.ext.declarative import declarative_base
   from sqlalchemy.orm import sessionmaker, Session
   from sqlalchemy.pool import QueuePool
   from contextlib import contextmanager
   import os

   DATABASE_URL = os.getenv(
       "DATABASE_URL",
       "postgresql://hydroponics_app:password@localhost/hydroponics"
   )

   # Connection pool configuration
   engine = create_engine(
       DATABASE_URL,
       poolclass=QueuePool,
       pool_size=5,          # Minimum connections
       max_overflow=15,      # Max additional connections (5+15=20 total)
       pool_pre_ping=True,   # Verify connections before use
       pool_recycle=3600,    # Recycle connections every hour
       echo=False            # Set to True for SQL logging
   )

   SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
   Base = declarative_base()

   @contextmanager
   def get_db_session() -> Session:
       """Context manager for database sessions"""
       session = SessionLocal()
       try:
           yield session
           session.commit()
       except Exception:
           session.rollback()
           raise
       finally:
           session.close()

   # FastAPI dependency
   def get_db():
       db = SessionLocal()
       try:
           yield db
       finally:
           db.close()
   ```

3. Create `backend/app/models/orm.py` for SQLAlchemy models

**Deliverables**:
- ✅ Connection pool initialized
- ✅ Pool metrics show 5 active connections minimum
- ✅ No connection timeouts under load

---

#### Task 1.2.3: Migrate SQLite Schema to PostgreSQL
**Assignee**: Backend Engineer
**Effort**: 4 hours

**Steps**:
1. Setup Alembic for migrations:
   ```bash
   cd backend
   alembic init alembic
   ```

2. Create initial migration:
   ```python
   # alembic/versions/001_initial_schema.py
   from alembic import op
   import sqlalchemy as sa

   def upgrade():
       # Clients table
       op.create_table(
           'clients',
           sa.Column('id', sa.Integer(), primary_key=True),
           sa.Column('name', sa.String(255), nullable=False),
           sa.Column('email', sa.String(255), unique=True),
           sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
           sa.Column('active', sa.Boolean(), default=True)
       )

       # Sensor configs table
       op.create_table(
           'sensor_configs',
           sa.Column('id', sa.Integer(), primary_key=True),
           sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id')),
           sa.Column('sensor_type', sa.String(50), nullable=False),
           sa.Column('sensor_id', sa.String(100), unique=True),
           sa.Column('location', sa.String(255)),
           sa.Column('config', sa.JSON())
       )

       # Add all other tables...
       # (crops, growth_stages, harvests, calibrations, varieties, events, etc.)

   def downgrade():
       op.drop_table('sensor_configs')
       op.drop_table('clients')
       # Drop all tables...
   ```

3. Run migration:
   ```bash
   alembic upgrade head
   ```

**Deliverables**:
- ✅ All tables created in PostgreSQL
- ✅ Schema matches SQLite structure
- ✅ Alembic migrations working

---

#### Task 1.2.4: Migrate Data from SQLite to PostgreSQL
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Create migration script `scripts/migrate_sqlite_to_postgres.py`:
   ```python
   import sqlite3
   import psycopg2
   from psycopg2.extras import execute_batch

   # Connect to both databases
   sqlite_conn = sqlite3.connect('hydroponics.db')
   postgres_conn = psycopg2.connect(
       "postgresql://hydroponics_app:password@localhost/hydroponics"
   )

   tables = [
       'clients', 'sensor_configs', 'crops', 'varieties',
       'growth_stages', 'harvests', 'calibrations', 'events'
   ]

   for table in tables:
       print(f"Migrating {table}...")

       # Read from SQLite
       sqlite_cursor = sqlite_conn.cursor()
       sqlite_cursor.execute(f"SELECT * FROM {table}")
       rows = sqlite_cursor.fetchall()

       if not rows:
           continue

       # Get column names
       columns = [desc[0] for desc in sqlite_cursor.description]

       # Write to PostgreSQL
       postgres_cursor = postgres_conn.cursor()
       placeholders = ','.join(['%s'] * len(columns))
       query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"

       execute_batch(postgres_cursor, query, rows)
       postgres_conn.commit()

       print(f"  ✅ Migrated {len(rows)} rows")

   print("Migration complete!")
   ```

2. Run migration:
   ```bash
   python scripts/migrate_sqlite_to_postgres.py
   ```

3. Verify data:
   ```sql
   SELECT 'clients' as table_name, COUNT(*) FROM clients
   UNION ALL
   SELECT 'crops', COUNT(*) FROM crops
   UNION ALL
   SELECT 'sensor_configs', COUNT(*) FROM sensor_configs;
   ```

**Deliverables**:
- ✅ All data migrated successfully
- ✅ Row counts match between SQLite and PostgreSQL
- ✅ Foreign key relationships intact

---

#### Task 1.2.5: Update Database Access Layer
**Assignee**: Backend Engineer
**Effort**: 3 hours

**Steps**:
1. Refactor `database.py` to use SQLAlchemy:
   ```python
   from sqlalchemy.orm import Session
   from typing import List, Optional
   from .models.orm import Client, SensorConfig, Crop

   class Database:
       def __init__(self, session: Session):
           self.session = session

       def create_client(self, name: str, email: str) -> Client:
           """Create new client"""
           client = Client(name=name, email=email)
           self.session.add(client)
           self.session.flush()  # Get ID without committing
           return client

       def get_client(self, client_id: int) -> Optional[Client]:
           """Get client by ID"""
           return self.session.query(Client).filter(
               Client.id == client_id
           ).first()

       def get_active_crops(self) -> List[Crop]:
           """Get all active crops"""
           return self.session.query(Crop).filter(
               Crop.status == 'active'
           ).all()

       # Update all other methods...
   ```

2. Update all callers to use new API
3. Remove old SQLite code

**Deliverables**:
- ✅ All database operations use SQLAlchemy
- ✅ No raw SQL queries (except complex analytics)
- ✅ Tests pass with PostgreSQL

---

## User Story 1.3: Implement Rate Limiting
**As a** system administrator
**I want** API endpoints to enforce rate limits
**So that** the system is protected from abuse and DDoS attacks

**Priority**: 🔴 P0 - CRITICAL
**Effort**: 5 story points (0.5 day)
**Dependencies**: Task 1.1.1 (FastAPI setup)

### Acceptance Criteria
- [ ] Rate limiting enforced on all POST endpoints
- [ ] Limit: 120 requests/minute per API key (2 req/sec average)
- [ ] Limit: 60 requests/minute per IP address (for public endpoints)
- [ ] Rate limit headers included in responses (`X-RateLimit-*`)
- [ ] 429 status returned when limit exceeded
- [ ] Retry-After header indicates when to retry

### Technical Tasks

#### Task 1.3.1: Install and Configure SlowAPI
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Install dependencies:
   ```bash
   pip install slowapi redis
   ```

2. Configure in `backend/app/main.py`:
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded
   from slowapi.middleware import SlowAPIMiddleware
   import redis

   # Redis backend for distributed rate limiting
   redis_client = redis.Redis(
       host=os.getenv('REDIS_HOST', 'localhost'),
       port=6379,
       db=0,
       decode_responses=True
   )

   # Initialize rate limiter
   limiter = Limiter(
       key_func=get_remote_address,
       storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:6379",
       strategy="fixed-window"  # or "moving-window"
   )

   app = FastAPI()
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   app.add_middleware(SlowAPIMiddleware)
   ```

**Deliverables**:
- ✅ Redis connection established
- ✅ Rate limiter middleware active

---

#### Task 1.3.2: Apply Rate Limits to Endpoints
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Add rate limits to sensor data endpoint:
   ```python
   from slowapi import Limiter
   from fastapi import Request

   @router.post("", status_code=202)
   @limiter.limit("120/minute")  # 2 req/sec average
   async def post_sensor_data(
       request: Request,
       reading: SensorReading,
       background_tasks: BackgroundTasks,
       api_key: str = Depends(verify_api_key),
       client_id: str = Depends(get_client_id)
   ):
       # ... existing code
   ```

2. Add custom rate limit key function (by API key instead of IP):
   ```python
   def get_api_key_identifier(request: Request):
       """Use API key as rate limit identifier"""
       api_key = request.headers.get("X-API-Key")
       if api_key:
           return f"api_key:{api_key}"
       return get_remote_address(request)

   # Use custom identifier
   limiter_by_key = Limiter(
       key_func=get_api_key_identifier,
       storage_uri="redis://localhost:6379"
   )

   @router.post("")
   @limiter_by_key.limit("120/minute")
   async def post_sensor_data(...):
       # ...
   ```

3. Apply to all endpoints:
   - POST `/api/data` - 120/min per API key
   - POST `/api/ac/control` - 60/min per API key
   - POST `/api/clients` - 10/min per IP
   - GET `/api/data/query` - 300/min per API key

**Deliverables**:
- ✅ Rate limits active on all endpoints
- ✅ 429 returned when exceeded
- ✅ Headers include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## User Story 1.4: Implement Async InfluxDB Batch Writer
**As a** backend developer
**I want** InfluxDB writes to be batched and asynchronous
**So that** sensor data ingestion doesn't block API responses

**Priority**: 🔴 P0 - CRITICAL
**Effort**: 3 story points (0.5 day)
**Dependencies**: Task 1.1.3 (Migrated POST endpoint)

### Acceptance Criteria
- [ ] InfluxDB writes use async batch API
- [ ] Batch size: 500 points or 10 seconds (whichever comes first)
- [ ] POST `/api/data` returns in <50ms (before InfluxDB write)
- [ ] Failed writes retry 3 times with exponential backoff
- [ ] Write success rate monitored (>99.9%)

### Technical Tasks

#### Task 1.4.1: Configure Async Batch Writer
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Update InfluxDB client configuration:
   ```python
   from influxdb_client import InfluxDBClient
   from influxdb_client.client.write_api import WriteOptions, WriteType
   import os

   # Initialize client
   influx_client = InfluxDBClient(
       url=os.getenv("INFLUXDB_URL"),
       token=os.getenv("INFLUXDB_TOKEN"),
       org=os.getenv("INFLUXDB_ORG")
   )

   # Configure batch writer
   write_options = WriteOptions(
       batch_size=500,           # Buffer up to 500 points
       flush_interval=10_000,    # Flush every 10 seconds
       jitter_interval=2_000,    # Add 0-2s random delay to distribute load
       retry_interval=5_000,     # Wait 5s before retry
       max_retries=3,            # Retry failed writes 3 times
       max_retry_delay=30_000,   # Max 30s between retries
       exponential_base=2,       # 5s, 10s, 20s retry delays
       max_close_wait=30_000,    # Wait 30s for pending writes on shutdown
       write_type=WriteType.batching
   )

   write_api = influx_client.write_api(write_options=write_options)
   ```

2. Add error callbacks:
   ```python
   def on_write_success(conf, data):
       """Called when batch write succeeds"""
       print(f"✅ Written {len(data)} points to InfluxDB")

   def on_write_error(conf, data, exception):
       """Called when batch write fails"""
       print(f"❌ Failed to write {len(data)} points: {exception}")
       # TODO: Send to dead letter queue

   def on_write_retry(conf, data, exception):
       """Called when write is retried"""
       print(f"🔄 Retrying write of {len(data)} points")

   write_api = influx_client.write_api(
       write_options=write_options,
       success_callback=on_write_success,
       error_callback=on_write_error,
       retry_callback=on_write_retry
   )
   ```

**Deliverables**:
- ✅ Batch writer configured
- ✅ Callbacks logging write status
- ✅ No blocking on write operations

---

#### Task 1.4.2: Implement Graceful Shutdown
**Assignee**: Backend Engineer
**Effort**: 1 hour

**Steps**:
1. Add shutdown handler:
   ```python
   from fastapi import FastAPI
   import atexit

   app = FastAPI()

   @app.on_event("shutdown")
   async def shutdown_event():
       """Flush pending writes before shutdown"""
       print("Shutting down... flushing pending writes")
       write_api.close()  # Waits for pending writes (max 30s)
       influx_client.close()
       print("InfluxDB client closed")

   # Also handle SIGTERM/SIGINT
   import signal

   def signal_handler(sig, frame):
       print(f"Received signal {sig}, shutting down gracefully")
       write_api.close()
       exit(0)

   signal.signal(signal.SIGTERM, signal_handler)
   signal.signal(signal.SIGINT, signal_handler)
   ```

**Deliverables**:
- ✅ Pending writes flushed on shutdown
- ✅ No data loss during restarts

---

---

# EPIC 2: Background Processing & Queuing
**Goal**: Decouple long-running tasks from API responses
**Business Value**: 100x faster API responses, reliable notification delivery
**Timeline**: Week 2 (Days 6-10)

---

## User Story 2.1: Setup Celery Task Queue
**As a** backend developer
**I want** a distributed task queue for background jobs
**So that** notifications, rule evaluation, and AC control don't block API responses

**Priority**: 🔴 P0 - CRITICAL
**Effort**: 8 story points (1 day)
**Dependencies**: Task 1.2.2 (PostgreSQL/Redis setup)

### Acceptance Criteria
- [ ] Celery configured with Redis broker
- [ ] 2 worker processes running
- [ ] Tasks can be queued and executed asynchronously
- [ ] Failed tasks retry with exponential backoff
- [ ] Flower monitoring dashboard accessible
- [ ] Task execution time <5 seconds for notifications

### Technical Tasks

#### Task 2.1.1: Install and Configure Celery
**Assignee**: Backend Engineer
**Effort**: 3 hours

**Steps**:
1. Install dependencies:
   ```bash
   pip install celery[redis] flower
   ```

2. Create `backend/app/celery_app.py`:
   ```python
   from celery import Celery
   import os

   celery_app = Celery(
       'hydroponics',
       broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
       backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
   )

   # Configuration
   celery_app.conf.update(
       task_serializer='json',
       accept_content=['json'],
       result_serializer='json',
       timezone='UTC',
       enable_utc=True,
       task_track_started=True,
       task_time_limit=300,      # 5 minutes max
       task_soft_time_limit=240,  # Warning at 4 minutes
       worker_prefetch_multiplier=4,
       worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
   )

   # Auto-discover tasks
   celery_app.autodiscover_tasks(['app.tasks'])
   ```

3. Create `backend/app/tasks/__init__.py`:
   ```python
   from .notifications import send_notification_task
   from .rules import evaluate_rules_task
   from .ac_control import control_ac_task

   __all__ = [
       'send_notification_task',
       'evaluate_rules_task',
       'control_ac_task'
   ]
   ```

**Deliverables**:
- ✅ Celery app configured
- ✅ Auto-discovery working

---

#### Task 2.1.2: Create Systemd Service for Workers
**Assignee**: DevOps Engineer
**Effort**: 1 hour

**Steps**:
1. Create `/etc/systemd/system/celery-worker.service`:
   ```ini
   [Unit]
   Description=Celery Worker for Hydroponics
   After=network.target redis.service

   [Service]
   Type=forking
   User=app
   Group=app
   WorkingDirectory=/opt/hydroponics/backend
   Environment="PATH=/opt/hydroponics/venv/bin"
   ExecStart=/opt/hydroponics/venv/bin/celery -A app.celery_app worker \
       --loglevel=info \
       --concurrency=2 \
       --max-tasks-per-child=1000 \
       --pidfile=/var/run/celery/%n.pid \
       --logfile=/var/log/celery/%n%I.log
   ExecReload=/bin/kill -HUP $MAINPID
   ExecStop=/bin/kill -TERM $MAINPID
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable celery-worker
   sudo systemctl start celery-worker
   ```

**Deliverables**:
- ✅ Workers start on boot
- ✅ 2 worker processes running

---

#### Task 2.1.3: Setup Flower Monitoring
**Assignee**: DevOps Engineer
**Effort**: 1 hour

**Steps**:
1. Create `/etc/systemd/system/celery-flower.service`:
   ```ini
   [Unit]
   Description=Flower Celery Monitoring
   After=network.target celery-worker.service

   [Service]
   Type=simple
   User=app
   WorkingDirectory=/opt/hydroponics/backend
   Environment="PATH=/opt/hydroponics/venv/bin"
   ExecStart=/opt/hydroponics/venv/bin/celery -A app.celery_app flower \
       --port=5555 \
       --broker=redis://localhost:6379/0
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. Configure NGINX reverse proxy for Flower:
   ```nginx
   location /flower/ {
       proxy_pass http://localhost:5555/;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;

       # Basic auth for security
       auth_basic "Flower Monitoring";
       auth_basic_user_file /etc/nginx/.htpasswd;
   }
   ```

**Deliverables**:
- ✅ Flower accessible at `http://server/flower/`
- ✅ Dashboard shows worker status

---

## User Story 2.2: Migrate Notifications to Background Tasks
**As a** system operator
**I want** notifications sent asynchronously
**So that** slow notification services don't block sensor data ingestion

**Priority**: 🔴 P0 - CRITICAL
**Effort**: 8 story points (1 day)
**Dependencies**: Task 2.1.1 (Celery setup)

### Acceptance Criteria
- [ ] All notification sends are Celery tasks
- [ ] POST `/api/data` returns in <100ms even if notifications fail
- [ ] Failed notifications retry 3 times (1min, 5min, 15min delays)
- [ ] Notification delivery rate >99%
- [ ] Dead letter queue captures permanently failed notifications

### Technical Tasks

#### Task 2.2.1: Create Notification Tasks
**Assignee**: Backend Engineer
**Effort**: 3 hours

**Steps**:
1. Create `backend/app/tasks/notifications.py`:
   ```python
   from ..celery_app import celery_app
   from ..notification_service import MultiChannelNotifier
   from typing import Dict, List
   import logging

   logger = logging.getLogger(__name__)

   @celery_app.task(
       bind=True,
       max_retries=3,
       default_retry_delay=60,  # 1 minute
       autoretry_for=(Exception,),
       retry_backoff=True,
       retry_backoff_max=900,  # 15 minutes max
       retry_jitter=True
   )
   def send_notification_task(
       self,
       subject: str,
       body: str,
       channels: List[str],
       severity: str = 'medium'
   ):
       """Send notification via configured channels"""
       try:
           notifier = MultiChannelNotifier()
           results = notifier.send(
               subject=subject,
               body=body,
               channels=channels,
               severity=severity
           )

           # Log results
           for channel, success in results.items():
               if success:
                   logger.info(f"✅ Sent to {channel}: {subject}")
               else:
                   logger.error(f"❌ Failed {channel}: {subject}")

           return results

       except Exception as exc:
           logger.error(f"Notification task failed: {exc}")
           # Will auto-retry due to autoretry_for
           raise

   @celery_app.task
   def send_escalation_alert(alert_id: int, escalation_level: int):
       """Send escalation alert for unacknowledged issues"""
       from ..alert_escalation import AlertEscalationManager

       manager = AlertEscalationManager()
       manager.escalate_alert(alert_id, escalation_level)
   ```

**Deliverables**:
- ✅ Tasks can be queued
- ✅ Retries work correctly
- ✅ Failures logged

---

#### Task 2.2.2: Update API Endpoints to Use Tasks
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Update `backend/app/routers/sensor_data.py`:
   ```python
   from ..tasks.notifications import send_notification_task

   @router.post("", status_code=202)
   async def post_sensor_data(
       reading: SensorReading,
       background_tasks: BackgroundTasks,
       api_key: str = Depends(verify_api_key),
       client_id: str = Depends(get_client_id)
   ):
       # Write to InfluxDB (async batch)
       background_tasks.add_task(write_to_influx, client_id, reading.dict())

       # Check if alert triggered
       alert = check_for_alert(reading)
       if alert:
           # Queue notification (doesn't block)
           send_notification_task.delay(
               subject=alert.subject,
               body=alert.body,
               channels=alert.channels,
               severity=alert.severity
           )

       return {"status": "accepted"}
   ```

2. Remove synchronous notification calls from:
   - `rule_engine.py`
   - `alert_escalation.py`
   - `drift_detection_service.py`

**Deliverables**:
- ✅ API returns immediately
- ✅ Notifications sent in background

---

#### Task 2.2.3: Implement Dead Letter Queue
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Create task error handler:
   ```python
   from celery.signals import task_failure

   @task_failure.connect
   def task_failed_handler(sender=None, task_id=None, exception=None, **kwargs):
       """Capture permanently failed tasks"""
       if sender.request.retries >= sender.max_retries:
           # Save to dead letter queue
           with get_db_session() as db:
               failed_task = FailedTask(
                   task_id=task_id,
                   task_name=sender.name,
                   args=sender.request.args,
                   kwargs=sender.request.kwargs,
                   exception=str(exception),
                   failed_at=datetime.utcnow()
               )
               db.add(failed_task)
   ```

2. Create admin endpoint to review failures:
   ```python
   @router.get("/admin/failed-tasks")
   async def get_failed_tasks(
       limit: int = 100,
       db: Session = Depends(get_db)
   ):
       """Get permanently failed tasks for manual retry"""
       failed = db.query(FailedTask).order_by(
           FailedTask.failed_at.desc()
       ).limit(limit).all()

       return {"failed_tasks": failed}
   ```

**Deliverables**:
- ✅ Failed tasks captured
- ✅ Admin can review failures

---

## User Story 2.3: Migrate Rule Engine to Background Tasks
**As a** backend developer
**I want** rule evaluation to happen asynchronously
**So that** complex rule logic doesn't delay sensor data responses

**Priority**: 🟠 P1 - HIGH
**Effort**: 5 story points (0.5 day)
**Dependencies**: Task 2.1.1 (Celery setup)

### Acceptance Criteria
- [ ] Rule evaluation is a Celery task
- [ ] Rules evaluated within 5 seconds of data ingestion
- [ ] Rule caching reduces database queries by 80%
- [ ] Batch rule evaluation for multiple sensors

### Technical Tasks

#### Task 2.3.1: Create Rule Evaluation Task
**Assignee**: Backend Engineer
**Effort**: 3 hours

**Steps**:
1. Create `backend/app/tasks/rules.py`:
   ```python
   from ..celery_app import celery_app
   from ..rule_engine import RuleEngine
   from ..cache import cache
   import logging

   logger = logging.getLogger(__name__)

   @celery_app.task
   def evaluate_rules_task(client_id: int, sensor_data: dict):
       """Evaluate all rules for sensor reading"""
       # Get cached rules (60 second TTL)
       cache_key = f"rules:client:{client_id}"
       rules = cache.get(cache_key)

       if not rules:
           engine = RuleEngine(client_id)
           rules = engine.get_active_rules()
           cache.set(cache_key, rules, ttl=60)

       # Evaluate each rule
       triggered_alerts = []
       for rule in rules:
           if rule.evaluate(sensor_data):
               triggered_alerts.append(rule)
               logger.info(f"Rule triggered: {rule.name}")

               # Queue notification
               from .notifications import send_notification_task
               send_notification_task.delay(
                   subject=rule.alert_subject,
                   body=rule.alert_body,
                   channels=rule.notification_channels,
                   severity=rule.severity
               )

       return len(triggered_alerts)

   @celery_app.task
   def batch_evaluate_rules(readings: List[dict]):
       """Evaluate rules for multiple readings (batch)"""
       for reading in readings:
           evaluate_rules_task.delay(
               client_id=reading['client_id'],
               sensor_data=reading
           )
   ```

**Deliverables**:
- ✅ Rules cached for 60 seconds
- ✅ Batch evaluation working

---

---

# EPIC 3: Database Optimization
**Goal**: Optimize database for high-volume queries
**Business Value**: 100x query performance, support millions of records
**Timeline**: Week 2 (Days 8-10)

---

## User Story 3.1: Add Comprehensive Database Indexes
**As a** database administrator
**I want** indexes on all frequently queried columns
**So that** queries remain fast as data grows to millions of records

**Priority**: 🟠 P1 - HIGH
**Effort**: 3 story points (0.5 day)
**Dependencies**: Task 1.2.3 (PostgreSQL migration)

### Acceptance Criteria
- [ ] Indexes added for all time-based queries
- [ ] Composite indexes for common filter combinations
- [ ] Query execution plans show index usage (no table scans)
- [ ] `/api/data/query` response time <100ms for 1M records

### Technical Tasks

#### Task 3.1.1: Create Index Migration
**Assignee**: Backend Engineer
**Effort**: 2 hours

**Steps**:
1. Create Alembic migration:
   ```python
   # alembic/versions/002_add_performance_indexes.py
   from alembic import op

   def upgrade():
       # Time-based indexes (DESC for recent-first queries)
       op.create_index('idx_events_created_at', 'events', ['created_at'], postgresql_using='btree', postgresql_concurrently=True)
       op.create_index('idx_harvests_date', 'harvests', ['harvest_date'], postgresql_using='btree')
       op.create_index('idx_calibrations_date', 'calibrations', ['calibration_date'], postgresql_using='btree')
       op.create_index('idx_growth_stages_started', 'growth_stages', ['started_at'])
       op.create_index('idx_growth_stages_ended', 'growth_stages', ['ended_at'])

       # Composite indexes for common queries
       op.create_index('idx_crops_status_variety', 'crops', ['status', 'variety_id'])
       op.create_index('idx_events_type_client_date', 'events', ['event_type', 'client_id', 'created_at'])
       op.create_index('idx_growth_stages_crop_status', 'growth_stages', ['crop_id', 'status'])

       # Foreign key indexes (performance + integrity)
       op.create_index('idx_crops_client', 'crops', ['client_id'])
       op.create_index('idx_crops_variety', 'crops', ['variety_id'])
       op.create_index('idx_harvests_crop', 'harvests', ['crop_id'])
       op.create_index('idx_calibrations_sensor', 'calibrations', ['sensor_id'])
       op.create_index('idx_sensor_configs_client', 'sensor_configs', ['client_id'])

       # Partial indexes for active records only
       op.execute("""
           CREATE INDEX idx_growth_stages_active
           ON growth_stages(crop_id, started_at)
           WHERE status = 'active';
       """)

       op.execute("""
           CREATE INDEX idx_crops_active
           ON crops(client_id, variety_id)
           WHERE status = 'active';
       """)

   def downgrade():
       op.drop_index('idx_events_created_at')
       # ... drop all indexes
   ```

2. Run migration:
   ```bash
   alembic upgrade head
   ```

3. Verify indexes:
   ```sql
   SELECT
       tablename,
       indexname,
       indexdef
   FROM pg_indexes
   WHERE schemaname = 'public'
   ORDER BY tablename, indexname;
   ```

**Deliverables**:
- ✅ All indexes created
- ✅ Index sizes reasonable (<20% of table size)

---

## User Story 3.2: Fix N+1 Query Problems
**As a** backend developer
**I want** database operations to use batch queries
**So that** hundreds of crops can be processed without hundreds of queries

**Priority**: 🟠 P1 - HIGH
**Effort**: 5 story points (0.5 day)
**Dependencies**: Task 1.2.5 (SQLAlchemy refactor)

### Acceptance Criteria
- [ ] Growth stage advancement uses single batch query
- [ ] Client service checks use joins instead of loops
- [ ] Sensor calibration checks batched
- [ ] Maximum 3 queries for any batch operation (1 SELECT, 1 UPDATE, 1 INSERT)

### Technical Tasks

#### Task 3.2.1: Refactor Growth Stage Manager
**Assignee**: Backend Engineer
**Effort**: 3 hours

**Steps**:
1. Update `growth_stage_manager.py`:
   ```python
   from sqlalchemy import text

   def check_and_advance_stages(self, db: Session):
       """Batch advance all eligible growth stages"""
       # Single query to find and update completed stages
       query = text("""
           WITH stages_to_complete AS (
               SELECT
                   gs.id,
                   gs.crop_id,
                   gs.stage_type,
                   EXTRACT(EPOCH FROM (NOW() - gs.started_at))/86400 as days_elapsed
               FROM growth_stages gs
               JOIN crops c ON gs.crop_id = c.id
               WHERE gs.status = 'active'
                 AND c.status = 'active'
                 AND EXTRACT(EPOCH FROM (NOW() - gs.started_at))/86400 >= gs.days_duration
           )
           UPDATE growth_stages
           SET status = 'completed', ended_at = NOW()
           WHERE id IN (SELECT id FROM stages_to_complete)
           RETURNING crop_id, stage_type;
       """)

       completed = db.execute(query).fetchall()

       if not completed:
           return

       # Batch insert new stages
       new_stages = [
           {
               'crop_id': crop_id,
               'stage_type': self.get_next_stage(stage_type),
               'started_at': datetime.utcnow(),
               'status': 'active'
           }
           for crop_id, stage_type in completed
       ]

       db.bulk_insert_mappings(GrowthStage, new_stages)
       db.commit()

       logger.info(f"Advanced {len(completed)} growth stages")
   ```

**Deliverables**:
- ✅ 100 crops updated in <100ms (vs 5+ seconds)
- ✅ Only 2 queries total

---

---

# EPIC 4: Production Hardening
**Goal**: Enterprise-grade monitoring, security, and reliability
**Business Value**: 99.9% uptime SLA, proactive issue detection
**Timeline**: Week 3 (Days 11-15)

---

## User Story 4.1: Implement Application Monitoring
**As a** DevOps engineer
**I want** comprehensive metrics and dashboards
**So that** I can monitor system health and identify issues proactively

**Priority**: 🟡 P2 - MEDIUM
**Effort**: 8 story points (1 day)
**Dependencies**: All previous tasks

### Acceptance Criteria
- [ ] Prometheus metrics exposed at `/metrics`
- [ ] Grafana dashboard showing key metrics
- [ ] Metrics: request rate, latency, error rate, queue depth, DB connections
- [ ] Alerts configured for critical thresholds
- [ ] 7-day retention for metrics

### Technical Tasks

(Tasks 4.1.1 - 4.1.4: Setup Prometheus, Grafana, configure metrics, create dashboards)

---

## User Story 4.2: Implement Data Retention Automation
**As a** system administrator
**I want** old data automatically cleaned up
**So that** storage costs don't grow unbounded

**Priority**: 🟡 P2 - MEDIUM
**Effort**: 3 story points (0.5 day)
**Dependencies**: Task 1.4.1 (InfluxDB async)

### Acceptance Criteria
- [ ] Cron job runs daily at 2 AM
- [ ] InfluxDB data >90 days deleted
- [ ] PostgreSQL events >1 year archived
- [ ] Deletion logged and monitored
- [ ] Manual dry-run mode available

### Technical Tasks

(Tasks 4.2.1 - 4.2.2: Create cleanup scripts, configure cron)

---

---

# 📋 SPRINT PLANNING TEMPLATE

## Sprint 1 (Week 1): Foundation
**Goal**: Unblock scaling to 50+ sensors

### Sprint Backlog
| Story ID | Story | Points | Owner | Status |
|----------|-------|--------|-------|--------|
| 1.1 | Migrate to FastAPI | 8 | Backend | 🔴 Todo |
| 1.2 | Connection Pooling | 13 | Backend | 🔴 Todo |
| 1.3 | Rate Limiting | 5 | Backend | 🔴 Todo |
| 1.4 | Async InfluxDB | 3 | Backend | 🔴 Todo |

**Total**: 29 points

---

## Sprint 2 (Week 2): Async Processing
**Goal**: 100x faster responses

### Sprint Backlog
| Story ID | Story | Points | Owner | Status |
|----------|-------|--------|-------|--------|
| 2.1 | Setup Celery | 8 | Backend | 🔴 Todo |
| 2.2 | Async Notifications | 8 | Backend | 🔴 Todo |
| 2.3 | Async Rules | 5 | Backend | 🔴 Todo |
| 3.1 | Database Indexes | 3 | Backend | 🔴 Todo |
| 3.2 | Fix N+1 Queries | 5 | Backend | 🔴 Todo |

**Total**: 29 points

---

## Sprint 3 (Week 3): Production Ready
**Goal**: Enterprise SaaS hardening

### Sprint Backlog
| Story ID | Story | Points | Owner | Status |
|----------|-------|--------|-------|--------|
| 4.1 | Monitoring | 8 | DevOps | 🔴 Todo |
| 4.2 | Data Retention | 3 | Backend | 🔴 Todo |
| 4.3 | Security Hardening | 5 | Backend | 🔴 Todo |
| 4.4 | Load Testing | 5 | QA | 🔴 Todo |

**Total**: 21 points

---

# 🎯 GITHUB ISSUES EXPORT

Would you like me to generate individual GitHub issue markdown files for each user story that you can import directly?

Each issue would include:
- Title, description, acceptance criteria
- Labels (priority, epic, effort)
- Checklist of technical tasks
- Estimated effort
- Dependencies

**Next Steps**:
1. Review this backlog
2. Approve sprint plan
3. Create GitHub issues (I can generate these)
4. Assign to team members
5. Start Sprint 1

Let me know if you want the GitHub issues generated!
