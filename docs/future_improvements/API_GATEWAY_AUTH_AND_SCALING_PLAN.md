# API Gateway, Authentication & Kubernetes Scaling Plan

**Project**: Technological Foods IoT Platform
**Date**: 2026-02-10
**Status**: Planning - Future Implementation Roadmap
**Context**: Based on full codebase review, scalability audit, 7 session history, and project analysis report

---

## Honest Assessment: Where You Are

Your system today is a **well-built monolith** running on a Raspberry Pi. That's not an insult - it's the right starting point. You have:

- 1 Python HTTP server handling everything (routing, auth, logic, storage)
- 1 shared `X-API-Key` for all clients and devices
- Docker Compose deployment (correctly chosen over K8s)
- 25+ REST endpoints, 147+ tests, solid documentation
- A clear B2B SaaS vision (Bronze/Silver/Gold tiers)

The problem is: **your ambition (multi-tenant SaaS with 100+ sensors across multiple clients) requires infrastructure your monolith can't provide.** The API Gateway is the bridge between where you are and where you're going.

---

## Why an API Gateway (and Why Now in the Planning)

Right now, `server.py` is doing 5 jobs:

```
Incoming Request
    |
    v
server.py does EVERYTHING:
  1. TLS termination     (it doesn't - plaintext HTTP)
  2. Authentication       (X-API-Key check inline)
  3. Rate limiting        (none)
  4. Request routing      (manual path matching)
  5. Business logic       (rule engine, notifications, etc.)
```

An API Gateway separates the **"who are you and should I let you in"** concerns from the **"what do you want to do"** concerns. This is the single most impactful architectural change for your scaling path because:

1. **It's the prerequisite for multi-tenant auth** - You can't do per-client JWT tokens when auth is hardcoded in your request handler
2. **It's the prerequisite for microservices** - Your MICROSERVICES_ARCHITECTURE.md vision requires a router in front
3. **It's the prerequisite for Kubernetes** - K8s Ingress IS an API Gateway; building gateway patterns now means K8s migration is mostly config changes later
4. **It protects your prototype** - You keep current code running behind the gateway while you evolve

---

## The Plan: Three Phases

```
PHASE 1                    PHASE 2                      PHASE 3
"Gateway Foundation"       "Real Authentication"        "K8s-Ready Architecture"
(Prototype-safe)           (Multi-tenant SaaS)          (When scale demands it)

  NGINX reverse proxy        JWT + OAuth2                 K8s Ingress Controller
  + TLS termination          Per-client API keys          Horizontal pod autoscaling
  + Basic rate limiting      RBAC (role-based access)     Service mesh (optional)
  + Keep X-API-Key           Tenant isolation             Multi-region
  + Health check routing     Token refresh flow           GitOps deployment
                             Device auth (separate)

  Effort: 1-2 days           Effort: 1-2 weeks            Effort: 2-4 weeks
  Cost: $0 extra             Cost: +$30-50/month          Cost: +$200-400/month
  Scale: 50 sensors          Scale: 200+ sensors          Scale: 1000+ sensors
  Trigger: NOW               Trigger: First paying        Trigger: 500+ sensors OR
           (planning)        client beyond pilot           multi-region requirement
```

---

## Phase 1: Gateway Foundation (Keep Prototyping)

**Goal**: Put a proper front door in front of your API without breaking anything that works today.

**When**: Next infrastructure sprint (before onboarding paying clients)

### Architecture

```
                    Internet / Local Network
                            |
                            v
                    ┌───────────────┐
                    │     NGINX     │ :443 (HTTPS)
                    │   (Gateway)   │ :80  (redirect to HTTPS)
                    │               │
                    │  - TLS/SSL    │
                    │  - Rate limit │
                    │  - CORS       │
                    │  - Logging    │
                    └───────┬───────┘
                            |
              ┌─────────────┼─────────────┐
              v             v             v
        /api/data      /api/docs     /api/health
        /api/rules     /api/ac       (no auth)
        /api/clients   /api/notify
              |             |
              v             v
        ┌─────────────────────┐
        │   server.py :3001   │  (unchanged - still uses X-API-Key)
        │   (your current     │
        │    monolith)        │
        └─────────────────────┘
```

### What NGINX Handles (So Your Code Doesn't Have To)

| Concern | Current (server.py) | Phase 1 (NGINX) |
|---------|---------------------|------------------|
| TLS/HTTPS | Not implemented | Let's Encrypt auto-cert |
| Rate limiting | Not implemented | `limit_req_zone` per IP |
| CORS headers | Not implemented | `add_header` directives |
| Request logging | Basic Python logging | Access logs + structured JSON |
| Health checks | Inline in handler | Separate upstream check |
| Static files | Served by Python | NGINX serves directly |
| Gzip compression | Not implemented | `gzip on` |

### NGINX Configuration (Production-Ready)

```nginx
# /etc/nginx/conf.d/agritech-gateway.conf

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=general:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=sensor_ingest:10m rate=60r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

# Upstream backend
upstream agritech_api {
    least_conn;
    server 127.0.0.1:3001 max_fails=3 fail_timeout=30s;
    # Phase 2: add server 127.0.0.1:3002 for redundancy
    keepalive 32;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # TLS (Let's Encrypt via certbot)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # CORS (for future dashboard frontend)
    add_header Access-Control-Allow-Origin "$http_origin" always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization, X-API-Key, Content-Type" always;

    # Gzip
    gzip on;
    gzip_types application/json text/plain;

    # Health check - no auth, no rate limit
    location /api/health {
        limit_req zone=general burst=10 nodelay;
        proxy_pass http://agritech_api;
        access_log off;
    }

    # Sensor data ingestion - higher rate limit (devices post frequently)
    location /api/data {
        limit_req zone=sensor_ingest burst=30 nodelay;
        proxy_pass http://agritech_api;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Limit body size (sensor payloads are small)
        client_max_body_size 16k;
    }

    # Management endpoints - stricter rate limit
    location /api/ {
        limit_req zone=general burst=20 nodelay;
        proxy_pass http://agritech_api;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Swagger docs - public, cached
    location /api/docs {
        limit_req zone=general burst=5 nodelay;
        proxy_pass http://agritech_api;
        proxy_cache_valid 200 5m;
    }
}
```

### What You Keep (Don't Touch)

- `X-API-Key` authentication in `server.py` - it still works, devices still use it
- All existing endpoints - unchanged
- All 147+ tests - still pass
- Docker Compose deployment - NGINX is just one more container

### Docker Addition

```yaml
# Add to docker-compose.yml
services:
  nginx-gateway:
    image: nginx:alpine
    container_name: agritech-gateway
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/agritech-gateway.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - nginx-logs:/var/log/nginx
    depends_on:
      - api  # your existing service
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
```

### My Honest Take on Phase 1

This is a **no-brainer**. NGINX as a reverse proxy is the industry standard. It gives you TLS (which you need before any paying client touches your system), rate limiting (your #1 security gap), and a clean separation point. Total effort is 1-2 days and it costs nothing. Do this before Phase 2.

---

## Phase 2: Real Authentication (Multi-Tenant Ready)

**Goal**: Per-client identity, scoped permissions, separate device vs human auth.

**When**: Before onboarding your second paying client (or first Gold-tier client)

### The Authentication Problem

Today you have ONE key that does everything:

```
X-API-Key: your-shared-key
  - Arduino sensors use it to POST data
  - Grafana uses it to GET data
  - Admin uses it to manage rules
  - Client B uses the SAME key as Client A
```

This means:
- Client A can read Client B's sensor data
- A compromised Arduino exposes admin endpoints
- No audit trail (who did what?)
- Can't enforce tier limits (Bronze gets same access as Gold)

### Dual Auth Strategy

The key insight: **devices and humans authenticate differently.**

```
                        ┌──────────────────────┐
                        │    NGINX Gateway     │
                        │   (TLS + Rate Limit) │
                        └──────────┬───────────┘
                                   |
                    ┌──────────────┴──────────────┐
                    v                              v
            Device Traffic                  Human/App Traffic
            (Arduino, sensors)              (Dashboard, Admin, API clients)
                    |                              |
                    v                              v
        ┌─────────────────┐            ┌─────────────────────┐
        │  Device Auth    │            │   OAuth2 / JWT      │
        │                 │            │                     │
        │  - Per-device   │            │  - Login endpoint   │
        │    API keys     │            │  - JWT access token │
        │  - Scoped to    │            │  - Refresh token    │
        │    POST /data   │            │  - Role-based       │
        │  - Tied to      │            │    (admin/viewer/   │
        │    client_id    │            │     operator)       │
        │  - Rate limited │            │  - Tenant-scoped    │
        │    per device   │            │                     │
        └────────┬────────┘            └──────────┬──────────┘
                 |                                 |
                 v                                 v
        ┌──────────────────────────────────────────────┐
        │              API Backend                     │
        │   request.client_id = "farm_algarve_01"      │
        │   request.role = "operator"                   │
        │   request.tier = "gold"                       │
        │                                              │
        │   Data filtered by client_id automatically    │
        └──────────────────────────────────────────────┘
```

### Device Authentication (Arduino/Sensors)

Devices can't do OAuth flows. They need simple, static credentials. But those credentials should be **scoped**.

```python
# Device API Key structure (stored in PostgreSQL)
{
    "key": "dev_ak_f7x9m2...",        # Unique per device
    "client_id": "farm_algarve_01",    # Owner
    "device_id": "arduino_greenhouse_1",
    "permissions": ["POST /api/data", "GET /api/commands"],
    "rate_limit": 60,                  # requests per minute
    "tier": "gold",                    # inherited from client
    "created_at": "2026-02-10",
    "last_used_at": "2026-02-10T14:30:00Z",
    "is_active": true
}
```

**Key decisions**:
- Prefix keys with `dev_ak_` so you can distinguish device keys from other tokens at the gateway level
- Each device key is scoped to only the endpoints that device needs
- Rate limits per device prevent a malfunctioning Arduino from flooding the system
- Keys are tied to a `client_id` so data isolation is enforced at auth time

### Human Authentication (JWT + OAuth2)

For dashboards, management APIs, and third-party integrations.

```python
# JWT token payload
{
    "sub": "user_42",                       # User ID
    "client_id": "farm_algarve_01",         # Tenant
    "role": "operator",                     # admin | operator | viewer
    "tier": "gold",                         # Client's service tier
    "permissions": [
        "read:sensors", "write:sensors",
        "read:rules", "write:rules",
        "read:clients",                      # Gold: can see own client data
        "read:analytics"                     # Gold: access analytics
    ],
    "exp": 1707580800,                      # 1 hour expiry
    "iat": 1707577200
}
```

**Role matrix** (maps to your existing B2B tiers):

| Permission | Viewer | Operator | Admin |
|------------|--------|----------|-------|
| Read sensor data | Own client | Own client | All clients |
| Write sensor data | No | Own devices | All devices |
| Manage rules | No | Own client | All clients |
| Manage clients | No | No | Yes |
| View analytics | Basic | Full (tier-limited) | Full |
| Manage users | No | No | Yes |
| Billing | No | View own | Full |

### Auth Flow Diagrams

**Device Registration** (one-time setup):

```
Admin Dashboard                     API Backend
     |                                  |
     |  POST /api/auth/devices          |
     |  { client_id, device_name }      |
     |--------------------------------->|
     |                                  |  Generate scoped API key
     |                                  |  Store in PostgreSQL
     |  { device_key: "dev_ak_..." }    |
     |<---------------------------------|
     |                                  |
     |  Flash key to Arduino config.h   |
     |                                  |
```

**User Login** (JWT flow):

```
Dashboard/Client                    API Gateway              API Backend
     |                                  |                        |
     |  POST /api/auth/login            |                        |
     |  { email, password }             |                        |
     |--------------------------------->|----------------------->|
     |                                  |                        | Verify credentials
     |                                  |                        | Generate JWT
     |  { access_token, refresh_token } |                        |
     |<---------------------------------|<-----------------------|
     |                                  |                        |
     |  GET /api/data/latest            |                        |
     |  Authorization: Bearer <jwt>     |                        |
     |--------------------------------->|  Validate JWT          |
     |                                  |  Extract client_id     |
     |                                  |  Forward with context  |
     |                                  |----------------------->|
     |                                  |                        | Filter by client_id
     |  { data: [...] }                 |                        |
     |<---------------------------------|<-----------------------|
```

### Data Isolation (The Multi-Tenant Key)

This is the most important piece for your B2B SaaS. Every query must be scoped to the authenticated client:

```python
# BEFORE (current - everyone sees everything)
def query_latest():
    query = f'from(bucket: "{INFLUXDB_BUCKET}") |> range(start: -1h) |> last()'

# AFTER (tenant-isolated)
def query_latest(client_id: str):
    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r["client_id"] == "{client_id}")
        |> last()
    '''
```

This pattern applies everywhere:
- InfluxDB queries filter by `client_id` tag
- PostgreSQL queries add `WHERE client_id = %s`
- Rule engine evaluates only client's own rules
- Notifications route to client's configured channels

### Gateway Changes for Phase 2

NGINX gains JWT validation (using `ngx_http_auth_jwt_module` or offloading to a lightweight auth service):

```nginx
# Phase 2 NGINX additions

# Device auth: API key passed through to backend
location /api/data {
    # Devices use X-API-Key header - validated by backend
    proxy_pass http://agritech_api;
}

# Human auth: JWT validated at gateway
location /api/ {
    # Auth service validates JWT and returns client context
    auth_request /internal/auth/validate;
    auth_request_set $client_id $upstream_http_x_client_id;
    auth_request_set $user_role $upstream_http_x_user_role;

    # Forward tenant context to backend
    proxy_set_header X-Client-ID $client_id;
    proxy_set_header X-User-Role $user_role;
    proxy_pass http://agritech_api;
}

# Internal auth validation endpoint
location = /internal/auth/validate {
    internal;
    proxy_pass http://auth_service:3010/validate;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header X-Original-URI $request_uri;
    proxy_set_header Authorization $http_authorization;
}
```

### Technology Choice: Auth Service

**My recommendation**: Don't build your own auth server from scratch.

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Custom Python auth** | Full control, simple | Security risk, maintenance burden | Only for device keys |
| **Keycloak** | Enterprise-grade, OIDC compliant | Heavy (1GB+ RAM), complex config | Too heavy for Pi |
| **Authelia** | Lightweight, Docker-friendly | Limited API key management | Good middle ground |
| **Custom FastAPI auth service** | Lightweight, fits your stack | You own the security code | Best for your scale |

**Recommended**: Small dedicated FastAPI auth service (~200 lines) that:
- Issues/validates JWTs for human users
- Validates device API keys
- Stores credentials in PostgreSQL (bcrypt-hashed)
- Runs as a separate container (~64MB RAM)

This keeps it simple and moves naturally into a K8s pod later.

### My Honest Take on Phase 2

This is where **most people over-engineer**. You don't need Keycloak, Auth0, or a full OIDC provider on day one. You need:

1. Per-device API keys (so Client A's Arduino can't see Client B's data)
2. JWT tokens for dashboard users (so you can build a real frontend)
3. `client_id` injected into every request (so data isolation is automatic)

Build the minimum auth service in-house. When you have 20+ clients and need SSO, federated login, or compliance (SOC2, GDPR), THEN evaluate managed auth providers. Not before.

---

## Config Server: The Glue Between Everything

**Goal**: Centralized, versioned, hot-reloadable configuration for all services and edge nodes.

**Why this matters**: You already built the seed of a Config Server - your `RuleEngine` is a mini config server for monitoring rules. It does CRUD via API, persists to JSON, and hot-reloads without restart. The problem is **everything else** can't do that.

### Your Configuration Problem Today

Your config is scattered across **6 different systems** with **3 different reload mechanisms**:

```
                         CURRENT STATE
                    (Configuration Chaos)

  .env files (2)          rules_config.json       variety_*.json (6)
  ├─ HTTP_PORT             ├─ 13 monitoring        ├─ Optimal ranges
  ├─ InfluxDB creds        │  rules                ├─ Growth stages
  ├─ Notification          ├─ Thresholds           ├─ Nutrient formulas
  │  channels              ├─ Actions              └─ Preventive actions
  └─ AC credentials        └─ Cooldowns
  RELOAD: restart           RELOAD: hot (API)       RELOAD: on crop create

  base_hydroponics.json    alert_escalation.py      notification_service.py
  ├─ Base sensor ranges    ├─ PREVENTIVE: 5min      ├─ SENSOR_META dict
  ├─ Calibration specs     ├─ WARNING: 10min         │  (min/max ranges)
  ├─ Maintenance schedule  ├─ CRITICAL: 15min        ├─ Cooldown: 900s
  └─ Time-based alerts     └─ URGENT: 15min          └─ Max history: 50
  RELOAD: on crop create   RELOAD: code change!      RELOAD: restart!
```

**The real pain**:
- Sensor ranges live in `base_hydroponics.json` AND in `notification_service.py` SENSOR_META. Change one, forget the other, and alerts fire on wrong thresholds.
- Escalation timing (5/10/15 minutes) is **hardcoded in Python**. Changing it requires editing code, committing, deploying, restarting.
- Adding a new notification channel requires env vars + code change + restart.
- When you go multi-instance (Phase 1 NGINX load balancer), each instance has its own `rules_config.json`. Operator changes a rule on instance 1, instance 2 doesn't know.
- When you go edge+cloud (Phase 3), each Pi needs to pull config from somewhere central. Currently there's no "somewhere central".

### What a Config Server Does

A Config Server is a **single source of truth** that all services query for their configuration. Your `RuleEngine` already proves the pattern works - the Config Server just extends it to everything.

```
                          FUTURE STATE
                    (Config Server Pattern)

                    ┌──────────────────────┐
                    │    Config Server      │
                    │    (FastAPI service)  │
                    │                      │
                    │  ┌────────────────┐  │
                    │  │  PostgreSQL    │  │  Versioned storage
                    │  │  config store  │  │  (who changed what, when)
                    │  └────────────────┘  │
                    │                      │
                    │  ┌────────────────┐  │
                    │  │  Redis cache   │  │  Fast reads
                    │  │  + pub/sub     │  │  Change notifications
                    │  └────────────────┘  │
                    │                      │
                    │  REST API:           │
                    │  GET  /config/{key}  │
                    │  PUT  /config/{key}  │
                    │  GET  /config/history│
                    │  POST /config/rollback│
                    └──────────┬───────────┘
                               |
              ┌────────────────┼────────────────┐
              |                |                |
              v                v                v
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ API      │    │ Edge Pi  │    │ Edge Pi  │
        │ Backend  │    │ Farm A   │    │ Farm B   │
        │          │    │          │    │          │
        │ Pulls:   │    │ Pulls:   │    │ Pulls:   │
        │ - rules  │    │ - rules  │    │ - rules  │
        │ - sensor │    │ - sensor │    │ - variety │
        │   meta   │    │   meta   │    │   configs│
        │ - escal. │    │ - variety│    │ - client  │
        │   levels │    │   config │    │   settings│
        │ - feature│    │ - feature│    │          │
        │   flags  │    │   flags  │    │          │
        └──────────┘    └──────────┘    └──────────┘
              |                |                |
              └──── Redis pub/sub ─────────────┘
                   (change notifications)
```

### Evolution Path: From Rule Engine to Config Server

The beauty is you don't build this all at once. You evolve what you already have:

#### Step 1: Consolidate Config Sources (Effort: 2-3 days)

Move hardcoded config into your existing rule_engine pattern. No new infrastructure needed.

**What changes**:

```python
# BEFORE: alert_escalation.py - hardcoded, requires code change
ESCALATION_LEVELS = [
    EscalationLevel(name="PREVENTIVE", wait_minutes=5, priority=3),
    EscalationLevel(name="WARNING", wait_minutes=10, priority=4),
    EscalationLevel(name="CRITICAL", wait_minutes=15, priority=5),
    EscalationLevel(name="URGENT", wait_minutes=15, priority=5),
]

# AFTER: loaded from config (same JSON pattern as rules_config.json)
# backend/api/escalation_config.json
{
    "version": 1,
    "escalation_levels": [
        {"name": "PREVENTIVE", "wait_minutes": 5, "priority": 3, "tags": "eyes"},
        {"name": "WARNING", "wait_minutes": 10, "priority": 4, "tags": "warning"},
        {"name": "CRITICAL", "wait_minutes": 15, "priority": 5, "tags": "rotating_light"},
        {"name": "URGENT", "wait_minutes": 15, "priority": 5, "tags": "rotating_light,sos"}
    ]
}

# alert_escalation.py now loads from file (hot-reloadable)
class EscalationManager:
    def __init__(self):
        self.config_file = Path(__file__).parent / 'escalation_config.json'
        self._load_config()

    def _load_config(self):
        with open(self.config_file) as f:
            data = json.load(f)
        self.levels = [EscalationLevel(**level) for level in data['escalation_levels']]
```

**Same treatment for**:
- `SENSOR_META` in notification_service.py → `sensor_meta_config.json`
- Notification cooldown → part of config, not env var
- AC temperature targets → `ac_config.json`

**Deduplicate**: sensor ranges defined ONCE in `base_hydroponics.json`, referenced everywhere else.

**Result**: All config in JSON files, all hot-reloadable via file watch or API reload endpoint.

#### Step 2: Add Config API Endpoints (Effort: 1-2 days)

Extend the pattern from your rules CRUD to all config types.

```
GET  /api/config                          # List all config namespaces
GET  /api/config/rules                    # Current rules (already exists)
GET  /api/config/escalation               # Escalation levels
GET  /api/config/sensors                  # Sensor metadata & ranges
GET  /api/config/varieties                # All variety configs
GET  /api/config/varieties/{name}         # Single variety
GET  /api/config/notifications            # Channel settings & cooldowns
GET  /api/config/features                 # Feature flags

PUT  /api/config/escalation               # Update escalation config
PUT  /api/config/sensors                  # Update sensor ranges
PUT  /api/config/notifications            # Update notification settings

POST /api/config/{namespace}/reload       # Force hot-reload from file
```

This is essentially your RuleEngine pattern repeated for each config domain. The endpoints share a common `ConfigManager` base class:

```python
class ConfigNamespace:
    """Base class for config namespaces - same pattern as RuleEngine."""

    def __init__(self, namespace: str, config_file: Path, schema: dict = None):
        self.namespace = namespace
        self.config_file = config_file
        self.schema = schema
        self._data = {}
        self._version = 0
        self._loaded_at = None
        self._load()

    def _load(self):
        with open(self.config_file) as f:
            self._data = json.load(f)
        self._version += 1
        self._loaded_at = datetime.utcnow()

    def get(self, key: str = None):
        if key:
            return self._data.get(key)
        return self._data

    def update(self, data: dict, changed_by: str = "api"):
        if self.schema:
            self._validate(data)
        self._data.update(data)
        self._version += 1
        self._save()
        self._log_change(changed_by, data)

    def _save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self._data, f, indent=2)

    def _log_change(self, changed_by, data):
        logger.info(f"Config [{self.namespace}] v{self._version} "
                    f"updated by {changed_by}: {list(data.keys())}")

    @property
    def metadata(self):
        return {
            "namespace": self.namespace,
            "version": self._version,
            "loaded_at": self._loaded_at.isoformat(),
            "file": str(self.config_file)
        }
```

**Result**: Every config domain is inspectable and modifiable at runtime through a consistent API.

#### Step 3: Move Config to Database + Versioning (Effort: 3-5 days)

When you move to PostgreSQL (from the scalability roadmap), config storage moves too. This is the real Config Server.

```sql
-- Config store with full audit trail
CREATE TABLE config_entries (
    id              SERIAL PRIMARY KEY,
    namespace       VARCHAR(50) NOT NULL,     -- 'rules', 'escalation', 'sensors', etc.
    key             VARCHAR(100) NOT NULL,    -- config key within namespace
    value           JSONB NOT NULL,           -- the actual config data
    version         INTEGER NOT NULL DEFAULT 1,
    environment     VARCHAR(20) DEFAULT 'production',  -- dev/staging/production
    client_id       VARCHAR(50),              -- NULL = global, otherwise client-specific
    is_active       BOOLEAN DEFAULT true,
    created_by      VARCHAR(100) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    superseded_at   TIMESTAMPTZ,              -- when this version was replaced

    UNIQUE(namespace, key, environment, client_id, version)
);

-- Fast lookup for active config
CREATE INDEX idx_config_active
    ON config_entries(namespace, key, environment, client_id)
    WHERE is_active = true;

-- Audit trail queries
CREATE INDEX idx_config_audit
    ON config_entries(namespace, created_at DESC);
```

**What this enables**:

```
GET  /api/config/rules?version=3           # Get specific version
GET  /api/config/rules/history             # Full change history
POST /api/config/rules/rollback?to=2       # Rollback to version 2
GET  /api/config/rules?client_id=farm_a    # Client-specific overrides
GET  /api/config/diff?from=2&to=5          # What changed between versions
```

**Example audit trail**:

```json
GET /api/config/escalation/history

{
  "namespace": "escalation",
  "history": [
    {
      "version": 3,
      "changed_by": "admin@agritech.pt",
      "changed_at": "2026-03-15T10:30:00Z",
      "change_summary": "Reduced CRITICAL wait to 10 minutes for Gold clients",
      "diff": {"escalation_levels[2].wait_minutes": {"old": 15, "new": 10}}
    },
    {
      "version": 2,
      "changed_by": "system:deploy",
      "changed_at": "2026-02-20T14:00:00Z",
      "change_summary": "Added URGENT level with SOS tag"
    },
    {
      "version": 1,
      "changed_by": "system:init",
      "changed_at": "2026-02-10T09:00:00Z",
      "change_summary": "Initial escalation config"
    }
  ]
}
```

#### Step 4: Hierarchical Config with Client Overrides (Effort: 2-3 days)

This is where it gets powerful for your B2B model. Config merges in layers:

```
    Base Config (applies to everyone)
         |
         v
    Tier Config (Bronze / Silver / Gold overrides)
         |
         v
    Client Config (per-farm overrides)
         |
         v
    Zone Config (per-greenhouse / per-tower overrides)
         |
         v
    Effective Config (what actually runs)
```

**Real example** - escalation timing varies by tier:

```json
// Base config (all clients)
{
    "escalation_levels": [
        {"name": "PREVENTIVE", "wait_minutes": 5},
        {"name": "WARNING",    "wait_minutes": 10},
        {"name": "CRITICAL",   "wait_minutes": 15},
        {"name": "URGENT",     "wait_minutes": 15}
    ]
}

// Gold tier override
{
    "tier": "gold",
    "escalation_levels": [
        {"name": "PREVENTIVE", "wait_minutes": 3},    // Faster for Gold
        {"name": "WARNING",    "wait_minutes": 5},     // Faster for Gold
        {"name": "CRITICAL",   "wait_minutes": 10},    // Faster for Gold
        {"name": "URGENT",     "wait_minutes": 5}      // Much faster - Gold pays for this
    ]
}

// Client-specific override (Farm Algarve requested custom)
{
    "client_id": "farm_algarve_01",
    "escalation_levels[0].wait_minutes": 2    // Even faster preventive alerts
}
```

**Resolution logic**:

```python
def resolve_config(namespace: str, client_id: str = None) -> dict:
    """Merge config layers: base → tier → client → zone."""
    # 1. Start with base
    config = get_config(namespace, environment="production")

    if client_id:
        # 2. Apply tier overrides
        client = get_client(client_id)
        tier_config = get_config(namespace, tier=client.tier)
        config = deep_merge(config, tier_config)

        # 3. Apply client-specific overrides
        client_config = get_config(namespace, client_id=client_id)
        config = deep_merge(config, client_config)

    return config
```

**This directly enables your SaaS tier differentiation**:

| Config | Bronze | Silver | Gold |
|--------|--------|--------|------|
| Alert escalation speed | Base (5/10/15 min) | Faster (3/7/12 min) | Fastest (2/5/10 min) |
| Data retention days | 7 | 30 | 90 |
| Notification channels | ntfy only | ntfy + email | ntfy + email + WhatsApp + SMS |
| Rule evaluation frequency | Every 30s | Every 10s | Every 2s (real-time) |
| Max rules per client | 15 | 50 | Unlimited |
| Calibration alert threshold | 5% drift | 3% drift | 2% drift |

All of this is **config, not code**. Upgrading a client from Bronze to Gold is a config change, not a deployment.

#### Step 5: Edge Sync for Multi-Site (Effort: 3-5 days)

When you have Pis at multiple farms (Phase 3 edge+cloud), each Pi needs its config from the central Config Server.

```
Central Config Server (Cloud)
         |
         |  HTTPS pull (every 60s) or WebSocket push
         |
    ┌────┴─────────────┬─────────────────┐
    v                  v                  v
  Pi Farm A          Pi Farm B          Pi Farm C
  Local cache        Local cache        Local cache
  (SQLite or JSON)   (SQLite or JSON)   (SQLite or JSON)

  If cloud unreachable → use last known config
  If cloud returns new version → apply + restart affected service
```

**Sync protocol** (simple and resilient):

```python
# On each edge Pi - config_sync.py
class ConfigSync:
    """Pulls config from central server, caches locally."""

    def __init__(self, server_url: str, client_id: str, device_key: str):
        self.server_url = server_url
        self.client_id = client_id
        self.device_key = device_key
        self.local_cache = Path("/data/config_cache")
        self.current_version = self._load_local_version()

    def sync(self):
        """Pull latest config if version changed."""
        try:
            response = requests.get(
                f"{self.server_url}/api/config/bundle",
                params={"client_id": self.client_id, "since_version": self.current_version},
                headers={"X-Device-Key": self.device_key},
                timeout=10
            )

            if response.status_code == 200:
                bundle = response.json()
                if bundle["version"] > self.current_version:
                    self._apply_config(bundle)
                    self.current_version = bundle["version"]
                    logger.info(f"Config updated to v{self.current_version}")

            elif response.status_code == 304:
                pass  # No changes

        except requests.ConnectionError:
            logger.warning("Config server unreachable, using cached config")
            # Continue with last known good config - resilient by design
```

**Result**: Edge nodes are always configured correctly, with graceful fallback when offline.

### Feature Flags (Built Into the Config Server)

Feature flags deserve special mention because they're a force multiplier during development. You can ship code for new features and control activation via config:

```json
// GET /api/config/features
{
    "features": {
        "whatsapp_notifications": {
            "enabled": false,
            "description": "WhatsApp channel via Twilio",
            "requires": ["TWILIO_ACCOUNT_SID", "TWILIO_WHATSAPP_FROM"],
            "rollout": "disabled"   // "disabled" | "internal" | "beta" | "all"
        },
        "drift_detection": {
            "enabled": true,
            "description": "Dual sensor drift detection",
            "rollout": "all",
            "config": {
                "degraded_threshold_pct": 2.0,
                "failing_threshold_pct": 5.0
            }
        },
        "data_marketplace": {
            "enabled": false,
            "description": "Anonymous data sales platform",
            "rollout": "disabled",
            "target_date": "2026-Q3"
        },
        "real_ph_sensor": {
            "enabled": false,
            "description": "Switch from simulated to real pH probe",
            "rollout": "beta",
            "beta_clients": ["farm_algarve_01"]
        },
        "predictive_alerts": {
            "enabled": false,
            "description": "ML-based predictive alerting",
            "rollout": "internal"
        }
    }
}
```

**Usage in code**:

```python
# Clean feature flag checks
if config_server.is_enabled("whatsapp_notifications"):
    notifier.add_channel(WhatsAppChannel())

if config_server.is_enabled("real_ph_sensor", client_id=request.client_id):
    reading = real_ph_probe.read()
else:
    reading = simulated_ph()
```

**Why this matters for your project specifically**:
- You have 4 notification channel stubs (WhatsApp, SMS, Email, ntfy). Feature flags let you ship the code now and enable per-client when they configure Twilio.
- Your simulated sensors (pH, EC, water level) can be swapped for real hardware per-device via feature flag. No code deployment needed when a client installs real probes.
- New features (data marketplace, predictive alerts, billing) can be developed on main branch behind flags and enabled when ready.

### Config Server Technology Choice

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Extend your RuleEngine pattern** | Already works, team knows it, zero new deps | JSON files don't scale to multi-instance | Steps 1-2 (start here) |
| **PostgreSQL config tables** | Versioning, audit trail, concurrent access | Need PostgreSQL first | Step 3 (when you migrate DB) |
| **Consul (HashiCorp)** | Industry standard, K/V store, health checks, service discovery | Another service to run, operational overhead | Only if you go K8s |
| **etcd** | K8s-native, strong consistency | Complex to operate standalone | Only within K8s |
| **Spring Cloud Config** | Enterprise-proven, Git-backed | Java ecosystem, heavy | Wrong tech stack |
| **Custom FastAPI service** | Fits your stack, lightweight, full control | You maintain it | Best for your scale |

**Recommended path**:
1. Steps 1-2: Extend RuleEngine pattern to all config (JSON files, same API style) - **now**
2. Step 3: Move to PostgreSQL-backed config when you do the DB migration - **with Phase 2**
3. Step 4: Add hierarchical client overrides when multi-tenant auth lands - **with Phase 2**
4. Step 5: Edge sync when deploying to multiple sites - **with Phase 3**
5. Consul/etcd: Only evaluate if you adopt K8s and need service discovery - **Phase 3+**

### How Config Server Connects to the Other Phases

```
Phase 1 (Gateway)          Config Server              Phase 3 (K8s)
─────────────────          ─────────────              ──────────────
NGINX reads rate           Config API serves           K8s ConfigMaps
limit config from          all service config          generated from
config files               with hot-reload             Config Server
       |                        |                           |
       └───── Step 1-2 ────────┘                           |
              (JSON files)                                  |
                                                           |
Phase 2 (Auth)             Config Server              K8s Secrets
──────────────             ─────────────              ──────────────
Auth service reads         PostgreSQL-backed           External Secrets
role permissions           with audit trail             Operator syncs
from config                + client overrides           from Config Server
       |                        |                           |
       └───── Step 3-4 ────────┘                           |
              (PostgreSQL)                                  |
                                                           |
                                Edge Pis
                                ────────
                                Pull config bundle
                                from central server
                                Cache locally
                                     |
                           └─── Step 5 ──┘
                                (HTTP sync)
```

### My Honest Take on Config Server

This is the **most underrated piece of infrastructure** in your roadmap. Everyone talks about gateways and Kubernetes, but centralized config is what actually lets you:

- Change behavior without deploying code
- Differentiate service tiers without code branches
- Roll back a bad config change in seconds
- Know exactly what configuration every client is running
- Onboard a new client by creating a config entry, not editing files

Your `RuleEngine` already proves the pattern. The journey from "rules are hot-reloadable" to "everything is hot-reloadable" is incremental, not revolutionary.

The one warning: **don't build a config server before you need one**. Steps 1-2 (consolidate hardcoded values into JSON, add API endpoints) give you 80% of the value with 20% of the effort. Steps 3-5 make sense only when multi-instance or multi-site is real, not planned.

---

## Phase 3: Kubernetes-Ready Architecture

**Goal**: Be able to move to K8s when scale demands it, without a rewrite.

**When**: 500+ sensors, OR multi-region deployment, OR 5+ microservices

### The Kubernetes Truth

Your DOCKER_COMPOSE_VS_KUBERNETES.md analysis was **correct**: K8s is overkill at your current scale. But here's the nuance - **you can be K8s-ready without running K8s**.

Being K8s-ready means:
- Every service runs in a container (you're already here)
- Services communicate via HTTP/gRPC, not file paths or shared memory
- Configuration comes from environment variables (you already do this)
- Health checks are exposed (you have `/api/health`)
- Stateless application layer (state lives in databases, not in-process)
- An API Gateway handles cross-cutting concerns

If you build Phases 1 and 2 correctly, **moving to K8s is a deployment change, not a code change**.

### K8s Migration Path (When the Time Comes)

```
Docker Compose (Current)              Kubernetes (Future)
─────────────────────────             ────────────────────────
docker-compose.yml          ──>       Helm chart / Kustomize
NGINX container             ──>       K8s Ingress Controller (NGINX or Traefik)
Docker restart: always      ──>       K8s Deployment + ReplicaSet
Manual scaling (2 instances)──>       HPA (Horizontal Pod Autoscaler)
.env files                  ──>       K8s Secrets + ConfigMaps
Docker health checks        ──>       K8s liveness/readiness probes
docker-compose up -d        ──>       kubectl apply / helm upgrade
GitHub Actions SSH deploy   ──>       ArgoCD / FluxCD (GitOps)
```

### What K8s Gives You (That Docker Compose Can't)

| Capability | Docker Compose | Kubernetes | When You Need It |
|------------|----------------|------------|------------------|
| Auto-scaling | Manual | HPA: auto-add pods based on CPU/memory/custom metrics | 500+ sensors with burst traffic |
| Self-healing | `restart: always` | Reschedule pods to healthy nodes | Multi-node cluster |
| Rolling updates | `docker-compose up -d` (brief downtime) | Zero-downtime rolling updates | SLA > 99.9% |
| Multi-region | Not supported | Federation / multi-cluster | International expansion |
| Service discovery | Docker DNS | CoreDNS + Service resources | 5+ microservices |
| Secret rotation | Manual .env update | External Secrets Operator | Compliance (SOC2) |
| Resource quotas | Docker limits | Namespace quotas, LimitRange | Multi-team |
| Network policies | Basic Docker network | Fine-grained pod-to-pod rules | Security hardening |

### Proposed K8s Architecture (When Ready)

```
                        ┌─────────────────────────────────┐
                        │         Cloud Provider           │
                        │    (Hetzner / DigitalOcean /     │
                        │     Scaleway - EU-based)         │
                        └────────────────┬────────────────┘
                                         |
                        ┌────────────────┴────────────────┐
                        │     K8s Ingress Controller       │
                        │  (NGINX Ingress or Traefik)      │
                        │                                  │
                        │  - TLS termination (cert-manager) │
                        │  - Rate limiting (annotations)    │
                        │  - JWT validation (middleware)    │
                        │  - API versioning (/v1/, /v2/)   │
                        └────────────────┬────────────────┘
                                         |
              ┌──────────┬───────────────┼───────────────┬──────────┐
              v          v               v               v          v
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Auth    │ │  Sensor  │ │   Crop   │ │ Analytics│ │  Client  │
        │ Service  │ │ Service  │ │ Service  │ │ Service  │ │ Service  │
        │ (2 pods) │ │ (3 pods) │ │ (2 pods) │ │ (2 pods) │ │ (2 pods) │
        │  HPA:    │ │  HPA:    │ │  HPA:    │ │  HPA:    │ │  HPA:    │
        │  min:2   │ │  min:2   │ │  min:1   │ │  min:1   │ │  min:1   │
        │  max:4   │ │  max:10  │ │  max:4   │ │  max:6   │ │  max:4   │
        └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
              |            |            |            |            |
              v            v            v            v            v
        ┌──────────────────────────────────────────────────────────────┐
        │                     Data Layer                               │
        │                                                              │
        │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
        │  │ PostgreSQL  │  │  InfluxDB   │  │    Redis    │         │
        │  │ (Managed or │  │  (Managed   │  │  (Cluster   │         │
        │  │  StatefulSet│  │   or Cloud) │  │   mode)     │         │
        │  │  + PgBouncer│  │             │  │             │         │
        │  └─────────────┘  └─────────────┘  └─────────────┘         │
        └──────────────────────────────────────────────────────────────┘
              |
              v
        ┌──────────────────────────────────┐
        │        Observability Stack        │
        │  Prometheus + Grafana + Loki      │
        │  (or Datadog/New Relic managed)   │
        └──────────────────────────────────┘
```

### Edge + Cloud Hybrid (Your Unique Advantage)

Your Raspberry Pi deployment is actually a **strategic asset**, not a limitation. When you move to K8s for the central platform, the Pis become edge nodes:

```
             Cloud (K8s Cluster)
        ┌──────────────────────────┐
        │  Central Platform        │
        │  - Auth service          │
        │  - Analytics service     │
        │  - Client management     │
        │  - Billing               │
        │  - Data marketplace      │
        │  - Dashboard frontend    │
        └────────────┬─────────────┘
                     |
        ┌────────────┼─────────────┐
        |            |             |
        v            v             v
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ Pi #1   │ │ Pi #2   │ │ Pi #3   │
   │ Farm A  │ │ Farm B  │ │ Farm C  │
   │ Algarve │ │ Alentejo│ │ Lisboa  │
   │         │ │         │ │         │
   │ Sensor  │ │ Sensor  │ │ Sensor  │
   │ Service │ │ Service │ │ Service │
   │ Local   │ │ Local   │ │ Local   │
   │ InfluxDB│ │ InfluxDB│ │ InfluxDB│
   │         │ │         │ │         │
   │ Syncs to│ │ Syncs to│ │ Syncs to│
   │ cloud   │ │ cloud   │ │ cloud   │
   └─────────┘ └─────────┘ └─────────┘
```

This hybrid model is powerful because:
- **Local resilience**: Sensors keep recording even if internet goes down
- **Reduced latency**: Rule engine evaluates locally (2ms vs 100ms round-trip)
- **Lower bandwidth**: Only sync aggregated data to cloud, not every 2-second reading
- **Cost efficiency**: Cheap Pi at the edge, shared K8s resources in the cloud
- **Client ownership**: Each client's Pi is on their premises, running their sensor service

### K8s Cost Estimate (EU Providers, When Ready)

| Provider | Setup | Monthly Cost | Notes |
|----------|-------|-------------|-------|
| **Hetzner Cloud** (recommended) | Managed K8s | ~$120-200/month | Best EU price/performance |
| DigitalOcean | DOKS | ~$150-250/month | Good docs, simple |
| Scaleway | Kapsule | ~$100-180/month | French, GDPR-native |
| OVHcloud | Managed K8s | ~$130-220/month | French, good for EU data residency |
| AWS EKS | Managed K8s | ~$300-500/month | Overkill, expensive |
| GKE | Managed K8s | ~$280-450/month | Great but pricey |

**Recommended**: Hetzner Cloud with managed K8s. EU-based, GDPR-compliant, excellent price.

### K8s Trigger Checklist (Don't Move Until Most Are True)

- [ ] 500+ sensors across 10+ clients
- [ ] Multi-region requirement (farms in different countries)
- [ ] 5+ microservices running in production
- [ ] Team of 3+ people touching infrastructure
- [ ] Monthly infrastructure budget > $500
- [ ] SLA requirement > 99.9% with contractual penalties
- [ ] Need for zero-downtime deployments
- [ ] Compliance requirements (SOC2, ISO 27001)

**If fewer than 4 boxes are checked, stay on Docker Compose.** It's the right choice.

### My Honest Take on Phase 3

Kubernetes is a **capability multiplier for teams and systems that have outgrown simpler tools**. It is NOT a quality multiplier - a poorly designed system on K8s is just a poorly designed system that's harder to debug.

The edge+cloud hybrid model is where I see the real value for your project. IoT platforms naturally benefit from this pattern: local processing at the edge, centralized intelligence in the cloud. When you get there, K8s is the natural choice for the cloud layer.

But here's what matters most: **Phases 1 and 2 make Phase 3 trivial.** If you containerize properly, use environment variables for config, communicate via HTTP, and separate auth from business logic - migrating to K8s is 2-4 weeks of infrastructure work, not a rewrite.

---

## What I Would NOT Do

Being honest about what's not worth your time right now:

1. **Don't adopt a service mesh (Istio/Linkerd)** - You don't have enough services to justify the 30% resource overhead and operational complexity. Re-evaluate at 8+ microservices.

2. **Don't build a custom API Gateway from scratch** - NGINX or Traefik give you 95% of what you need. Kong is excellent but adds operational weight. Use NGINX for Phase 1-2, evaluate Kong or Traefik when moving to K8s.

3. **Don't implement OAuth2 for device auth** - Devices need simple, static credentials. OAuth token refresh on an Arduino is painful and error-prone. Per-device API keys with scoped permissions are the right pattern for IoT.

4. **Don't move to K8s before fixing the synchronous I/O** - Your scalability audit correctly identified this as P0. K8s can't fix a blocking architecture; it just runs more instances of a slow service. Fix the fundamentals first.

5. **Don't use managed auth providers (Auth0, Cognito) yet** - At $0.05/MAU it seems cheap, but the vendor lock-in and complexity aren't worth it under 1000 users. Build simple JWT auth in-house, migrate to a provider when you need SSO/federation.

6. **Don't multi-region before multi-tenant** - Data isolation between clients on a single region is more important than geographic distribution. Get tenant isolation right first.

---

## Implementation Priority Order

```
Priority  | Task                                      | Phase  | Effort  | Prerequisite
──────────┼───────────────────────────────────────────┼────────┼─────────┼─────────────
    1      | Fix synchronous I/O (scalability audit P0)| -      | 1 week  | None
    2      | NGINX reverse proxy + TLS                 | 1      | 1-2 days| None
    3      | NGINX rate limiting                       | 1      | 0.5 day | #2
    4      | Consolidate hardcoded config into JSON    | Config | 2-3 days| None
    5      | Add config API endpoints (CRUD all config)| Config | 1-2 days| #4
    6      | FastAPI migration (from BaseHTTPHandler)   | -      | 1 week  | #1
    7      | Per-device API keys                       | 2      | 2-3 days| #6
    8      | JWT auth for human users                  | 2      | 3-5 days| #6, #7
    9      | Tenant data isolation (client_id filter)  | 2      | 3-5 days| #7, #8
   10      | Redis caching layer                       | -      | 1-2 days| #6
   11      | Celery task queue for notifications       | -      | 2-3 days| #6, #10
   12      | PostgreSQL migration (from SQLite)         | -      | 3-5 days| #6
   13      | Config versioning + audit trail in PG     | Config | 2-3 days| #12
   14      | Hierarchical config (tier/client overrides)| Config | 2-3 days| #9, #13
   15      | Feature flags system                      | Config | 1-2 days| #5 or #13
   ---     | --- K8s boundary (only if triggers met) ---| ---   | ---     | ---
   16      | Containerize API into proper Dockerfile   | 3      | 1-2 days| #6
   17      | Helm chart / Kustomize manifests           | 3      | 3-5 days| #16
   18      | K8s Ingress replacing NGINX container      | 3      | 2-3 days| #17
   19      | HPA + resource limits tuning              | 3      | 2-3 days| #17
   20      | GitOps pipeline (ArgoCD/FluxCD)            | 3      | 3-5 days| #17
   21      | Edge config sync for multi-site Pis       | Config | 3-5 days| #13, #16
```

---

## Summary

| Phase | What | Why | When |
|-------|------|-----|------|
| **1** | NGINX Gateway + TLS + Rate Limiting | Front door security, TLS for clients, DDoS protection | Before first paying client |
| **Config (Steps 1-2)** | Consolidate config + add CRUD API | Eliminate hardcoded values, enable runtime changes | Alongside Phase 1 |
| **2** | Device API keys + JWT + Tenant isolation | Multi-tenant SaaS, data separation, real auth | Before second paying client |
| **Config (Steps 3-4)** | PostgreSQL config + tier/client overrides | Versioned config, audit trail, SaaS tier differentiation | Alongside Phase 2 |
| **3** | K8s migration with edge+cloud hybrid | Horizontal scaling, multi-region, HA | When scale demands it (500+ sensors) |
| **Config (Step 5)** | Edge sync for multi-site Pis | Central config pushed to all farm nodes | Alongside Phase 3 |

Three threads weave through the entire plan:
- **Gateway**: starts as NGINX, gains JWT validation, becomes K8s Ingress Controller
- **Config Server**: starts as JSON files with API, moves to PostgreSQL with versioning, syncs to edge nodes
- **Auth**: starts as shared API key, evolves to device keys + JWT, integrates with gateway

Each builds on the last. Nothing gets thrown away. Your existing RuleEngine pattern is the seed for the Config Server. Your existing X-API-Key is the seed for proper auth. Your existing Docker Compose is the seed for K8s-ready containers.

**Build the right thing at the right time. Phase 1 now, Phase 2 when revenue justifies it, Phase 3 when scale demands it.**
