# Hostel Management Backend — Module 1: Authentication & Authorization

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Folder Structure](#3-folder-structure)
4. [Database Design](#4-database-design)
5. [Design Decisions](#5-design-decisions)
6. [Migration System](#6-migration-system)
7. [Docker Architecture](#7-docker-architecture)
8. [API Reference](#8-api-reference)
9. [Security Architecture](#9-security-architecture)
10. [Setup & Running](#10-setup--running)
11. [Testing the APIs](#11-testing-the-apis)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. Project Overview

This is the **IAM (Identity & Access Management)** foundation for a multi-tenant Hostel Management SaaS platform.

It supports:
- Multiple hostel **owners** (tenants)
- Multiple **hostels** under one owner
- Role-based access control (RBAC) with fine-grained permissions
- Stateless JWT authentication with refresh token rotation
- OTP-based password recovery
- Account lockout, audit logging, and password history

Every future module (Hostels, Students, Employees, Expenses, Inventory) depends on this module.

---

## 2. Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Framework    | FastAPI 0.111                       |
| Validation   | Pydantic v2                         |
| Database     | MongoDB 7.0 (Docker container)      |
| Async Driver | Motor + PyMongo                     |
| Auth         | JWT (python-jose), BCrypt (passlib) |
| Config       | pydantic-settings + .env            |
| Server       | Uvicorn (ASGI)                      |
| Migrations   | Custom Flyway-style Python runner   |
| Containers   | Docker + Docker Compose             |

---

## 3. Folder Structure

```
hostel-management-backend/
├── app/
│   ├── api/
│   │   ├── auth.py              # Auth endpoints (login, logout, OTP, password)
│   │   └── users.py             # /me, /roles, /permissions
│   ├── services/
│   │   ├── auth_service.py      # Login, logout, token refresh logic
│   │   ├── otp_service.py       # OTP generation and verification
│   │   └── password_service.py  # Reset and change password logic
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── role_repository.py
│   │   ├── otp_repository.py
│   │   ├── refresh_token_repository.py
│   │   ├── password_history_repository.py
│   │   └── audit_log_repository.py
│   ├── models/                  # MongoDB document factory functions
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── refresh_token.py
│   │   ├── otp_request.py
│   │   ├── password_history.py
│   │   └── audit_log.py
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── auth.py
│   │   └── user.py
│   ├── core/
│   │   ├── config.py            # Settings from .env
│   │   ├── database.py          # Motor client
│   │   ├── security.py          # BCrypt + password validation
│   │   ├── jwt.py               # Token creation and decoding
│   │   └── dependencies.py      # FastAPI dependency injection
│   ├── migrations/
│   │   ├── migrator.py          # Flyway-style migration runner
│   │   ├── seed.py              # Legacy local seed (non-Docker use)
│   │   └── versions/
│   │       ├── V1__create_indexes.py
│   │       ├── V2__seed_roles_and_permissions.py
│   │       └── V3__seed_default_owner.py
│   └── main.py                  # FastAPI app entry point
├── docker/
│   └── wait-for-mongo.sh        # Polls Mongo readiness before migrator runs
├── Dockerfile                   # API service image
├── Dockerfile.migrator          # Migrator one-shot container image
├── docker-compose.yml           # Orchestrates mongo + migrator + api
├── .env                         # Local development environment
├── .env.docker                  # Docker environment (used by compose)
├── requirements.txt
└── DOCUMENTATION.md
```

---

## 4. Database Design

MongoDB is used as the database. All collections use MongoDB's native `_id` (ObjectId) as the primary key, serialized as string `id` in API responses.

---

### Collection: `users`

Stores all system users (owners, managers, staff).

| Field               | Type      | Description                                      |
|---------------------|-----------|--------------------------------------------------|
| `_id`               | ObjectId  | Primary key                                      |
| `owner_id`          | string    | Reference to the owner user (for multi-tenancy)  |
| `employee_id`       | string    | Link to employee record (future module)          |
| `first_name`        | string    |                                                  |
| `last_name`         | string    |                                                  |
| `email`             | string    | Unique, lowercase, sparse index                  |
| `mobile`            | string    | Unique, sparse index                             |
| `password_hash`     | string    | BCrypt hash                                      |
| `role_id`           | string    | Reference to `roles` collection                  |
| `status`            | enum      | `active`, `inactive`, `locked`, `deleted`, `pending_verification` |
| `last_login`        | datetime  |                                                  |
| `failed_attempts`   | int       | Resets on successful login                       |
| `is_locked`         | bool      |                                                  |
| `locked_until`      | datetime  | Auto-unlock after this time                      |
| `is_email_verified` | bool      |                                                  |
| `is_mobile_verified`| bool      |                                                  |
| `created_at`        | datetime  |                                                  |
| `created_by`        | string    | User ID who created this record                  |
| `updated_at`        | datetime  |                                                  |
| `updated_by`        | string    |                                                  |
| `deleted_at`        | datetime  | Soft delete — null means not deleted             |

**Indexes:** `email` (unique, sparse), `mobile` (unique, sparse)

---

### Collection: `roles`

| Field          | Type     | Description                        |
|----------------|----------|------------------------------------|
| `_id`          | ObjectId |                                    |
| `role_name`    | string   | e.g., Owner, Manager, Chef         |
| `description`  | string   |                                    |
| `is_system_role` | bool   | System roles cannot be deleted     |
| `created_at`   | datetime |                                    |

**Seeded roles:** Owner, Manager, Supervisor, Chef, Cleaning Head, Helper

---

### Collection: `permissions`

| Field         | Type     | Description                        |
|---------------|----------|------------------------------------|
| `_id`         | ObjectId |                                    |
| `module`      | string   | e.g., Student, Expense, Hostel     |
| `action`      | string   | e.g., Create, Read, Update, Delete |
| `description` | string   |                                    |

---

### Collection: `role_permissions`

Many-to-many join between `roles` and `permissions`.

| Field           | Type   | Description              |
|-----------------|--------|--------------------------|
| `_id`           | ObjectId |                        |
| `role_id`       | string | Reference to `roles`     |
| `permission_id` | string | Reference to `permissions` |

---

### Collection: `refresh_tokens`

| Field        | Type     | Description                                      |
|--------------|----------|--------------------------------------------------|
| `_id`        | ObjectId |                                                  |
| `user_id`    | string   |                                                  |
| `token_hash` | string   | SHA-256 hash of the raw refresh token            |
| `expiry_date`| datetime |                                                  |
| `created_at` | datetime |                                                  |
| `revoked_at` | datetime | Null = active, set = revoked                     |
| `ip_address` | string   |                                                  |
| `device_info`| string   | User-Agent string                                |

**Indexes:** `token_hash`, `user_id`

---

### Collection: `otp_requests`

| Field       | Type     | Description                                          |
|-------------|----------|------------------------------------------------------|
| `_id`       | ObjectId |                                                      |
| `user_id`   | string   |                                                      |
| `otp`       | string   | 6-digit numeric OTP                                  |
| `purpose`   | enum     | `forgot_password`, `email_verification`, `mobile_verification` |
| `expiry_time`| datetime| OTP expires after 10 minutes                        |
| `attempts`  | int      | Max 5 attempts before OTP is invalidated             |
| `is_used`   | bool     | Marked true after successful verification            |
| `created_at`| datetime |                                                      |

**Index:** `(user_id, purpose)`

---

### Collection: `password_history`

| Field          | Type     | Description                          |
|----------------|----------|--------------------------------------|
| `_id`          | ObjectId |                                      |
| `user_id`      | string   |                                      |
| `password_hash`| string   | BCrypt hash of old password          |
| `created_at`   | datetime |                                      |

Stores last 5 password hashes per user to prevent reuse.

---

### Collection: `audit_logs`

| Field       | Type     | Description                                      |
|-------------|----------|--------------------------------------------------|
| `_id`       | ObjectId |                                                  |
| `user_id`   | string   | Null for anonymous actions                       |
| `action`    | string   | `login`, `logout`, `failed_login`, `password_reset`, `password_changed` |
| `module`    | string   | e.g., `auth`                                     |
| `ip_address`| string   |                                                  |
| `device`    | string   | User-Agent                                       |
| `browser`   | string   |                                                  |
| `meta`      | object   | Additional context                               |
| `created_at`| datetime |                                                  |

**Indexes:** `user_id`, `created_at`

---

### Entity Relationship Diagram

```
Users ──────────── Roles
  |                  |
  |              Role_Permissions
  |                  |
  |              Permissions
  |
  ├── Refresh_Tokens
  ├── OTP_Requests
  ├── Password_History
  └── Audit_Logs
```

---

## 5. Design Decisions

### Why Docker?
- Eliminates "works on my machine" problems — MongoDB version, config, and credentials are locked in `docker-compose.yml`.
- The `migrator` container runs once, applies all pending migrations, then exits. The `api` container only starts after the migrator completes successfully (`service_completed_successfully` condition).
- MongoDB data is persisted in a named Docker volume (`mongo_data`) so data survives container restarts.
- The `mongo` service exposes port `27017` to the host so MongoDB Compass can connect for inspection.

### Why a Custom Migration Runner Instead of Flyway?
- Flyway is a Java tool designed for SQL databases — it has no native MongoDB support.
- The custom runner in `app/migrations/migrator.py` replicates Flyway's core contract:
  - Versioned files: `V{n}__{description}.py`
  - Applied versions tracked in a `schema_migrations` collection
  - Idempotent: already-applied versions are skipped
  - Ordered: versions always run in numeric order
  - Fail-fast: if any migration fails, the process exits with code 1 and the error is recorded
- Each migration file exposes `async def up(db)` and `async def down(db)` — matching Flyway's up/down pattern.
- Adding a new migration is as simple as creating `V4__your_change.py` in the `versions/` folder.

### Why MongoDB?
- Schema flexibility is ideal for a SaaS where different hostel owners may have different configurations.
- Embedded documents and flexible fields make it easy to extend models without migrations.
- Motor provides async I/O which pairs perfectly with FastAPI.

### Why ObjectId instead of UUID?
- MongoDB's native ObjectId is more efficient for indexing and querying.
- It is serialized to a string `id` in all API responses for consistency.
- UUIDs can be added as a separate `tenant_id` field when needed for cross-database sync.

### Stateless JWT + Refresh Token Rotation
- Access tokens are short-lived (30 min) and stateless — no DB lookup needed per request.
- Refresh tokens are stored as SHA-256 hashes in MongoDB — never in plain text.
- On each refresh, the old token is revoked and a new one is issued (rotation) — prevents token replay attacks.

### Repository Pattern
- All database operations are isolated in repository classes.
- Services contain business logic and call repositories.
- This makes it easy to swap the database layer or write unit tests with mocks.

### Password Security
- BCrypt with default cost factor (12 rounds).
- Password strength enforced via regex: min 8 chars, uppercase, lowercase, digit, special character.
- Last 5 passwords stored as hashes — new password is checked against all of them.
- On password reset/change, all refresh tokens for the user are revoked, forcing re-login on all devices.

### Account Lockout
- After 5 consecutive failed login attempts, the account is locked for 30 minutes.
- Lock is automatically lifted on the next login attempt after the lock period expires (no manual admin action needed for MVP).

### OTP Design
- 6-digit numeric OTP, expires in 10 minutes.
- Max 5 verification attempts per OTP record.
- OTP is marked `is_used = true` after successful verification — cannot be reused.
- The `forgot_password` flow requires OTP verification inline with `reset-password` — the OTP is verified again at reset time, not just at verify-otp time, preventing replay.

### Multi-Tenancy Foundation
- `owner_id` on the `users` collection identifies which tenant a user belongs to.
- All future business collections (Hostels, Students, Employees) should include `owner_id` and `hostel_id` for data isolation.
- `created_by`, `updated_by`, `deleted_at` are on every document for full audit trail.

### Soft Deletes
- Users are never hard-deleted. `deleted_at` is set and `status` is set to `deleted`.
- Queries filter `deleted_at: null` to exclude deleted records.

### Dev vs Production OTP
- In development, OTP is printed to the console (`[DEV] OTP for ...`).
- In production, replace the `print` in `otp_service.py` with an SMS/Email provider (e.g., AWS SNS, Twilio, SendGrid).

---

## 6. Migration System

### How It Works

```
Docker Compose starts migrator container
        │
        ▼
wait-for-mongo.sh polls MongoDB with ping
        │
        ▼ (MongoDB ready)
python -m app.migrations.migrator
        │
        ├── Discovers V1, V2, V3 ... files in versions/
        ├── Reads schema_migrations collection for applied versions
        ├── Skips already-applied versions
        ├── Runs pending up(db) functions in order
        ├── Records each result in schema_migrations
        └── Exits 0 (success) or 1 (failure)
                │
                ▼ (exit 0)
        api container starts
```

### schema_migrations Collection

| Field        | Type     | Description                          |
|--------------|----------|--------------------------------------|
| `version`    | int      | Migration version number (e.g., 1)   |
| `description`| string   | From filename (e.g., `create_indexes`) |
| `applied_at` | datetime |                                      |
| `success`    | bool     |                                      |
| `error`      | string   | Populated on failure                 |

### Adding a New Migration

1. Create `app/migrations/versions/V4__your_description.py`
2. Implement `async def up(db)` and `async def down(db)`
3. Run `docker compose up migrator` — only V4 will run (V1–V3 already applied)

```python
# Example: V4__add_tenant_id_index.py
async def up(db):
    await db["users"].create_index("tenant_id")
    print("  [V4] tenant_id index created")

async def down(db):
    await db["users"].drop_index("tenant_id_1")
```

---

## 7. Docker Architecture

### Services

```
┌─────────────────────────────────────────────────────┐
│                  Docker Network                      │
│                                                     │
│  ┌──────────┐    healthy    ┌──────────────┐        │
│  │  mongo   │ ─────────────▶│   migrator   │        │
│  │  :27017  │               │  (one-shot)  │        │
│  └──────────┘               └──────┬───────┘        │
│       │                            │ completed       │
│       │                     ┌──────▼───────┐        │
│       └─────────────────────▶     api      │        │
│                              │   :8000     │        │
│                              └─────────────┘        │
└─────────────────────────────────────────────────────┘

Host ports exposed:
  27017 → mongo   (MongoDB Compass access)
  8000  → api     (API access)
```

### Startup Order

1. `mongo` starts and passes its healthcheck (`mongosh ping`)
2. `migrator` starts, `wait-for-mongo.sh` confirms connectivity, runs all pending migrations, exits 0
3. `api` starts only after `migrator` exits successfully

### Environment Files

| File          | Used by          | Purpose                              |
|---------------|------------------|--------------------------------------|
| `.env`        | Local dev        | Points to `localhost:27017`          |
| `.env.docker` | Docker Compose   | Points to `mongo:27017` (service name) |

---

## 8. API Reference

Base URL: `http://localhost:8000`

### Authentication Endpoints

| Method | Endpoint                    | Auth Required | Description                        |
|--------|-----------------------------|---------------|------------------------------------|
| POST   | `/api/auth/login`           | No            | Login with email/mobile + password |
| POST   | `/api/auth/logout`          | Yes           | Revoke refresh token               |
| POST   | `/api/auth/refresh-token`   | No            | Get new access token               |
| POST   | `/api/auth/forgot-password` | No            | Send OTP to email/mobile           |
| POST   | `/api/auth/verify-otp`      | No            | Verify OTP                         |
| POST   | `/api/auth/reset-password`  | No            | Reset password using OTP           |
| POST   | `/api/auth/change-password` | Yes           | Change password (logged-in user)   |

### User & Role Endpoints

| Method | Endpoint           | Auth Required | Description              |
|--------|--------------------|---------------|--------------------------|
| GET    | `/api/users/me`    | Yes           | Get current user profile |
| GET    | `/api/roles`       | Yes           | List all roles           |
| GET    | `/api/permissions` | Yes           | List all permissions     |

### Request/Response Examples

**POST /api/auth/login**
```json
// Request
{
  "identifier": "owner@hostel.com",
  "password": "Owner@1234"
}

// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "abc123...",
  "token_type": "bearer"
}
```

**POST /api/auth/forgot-password**
```json
// Request
{ "identifier": "owner@hostel.com" }

// Response 200
{ "message": "If the account exists, an OTP has been sent" }
```

**POST /api/auth/verify-otp**
```json
// Request
{
  "identifier": "owner@hostel.com",
  "otp": "123456",
  "purpose": "forgot_password"
}
```

**POST /api/auth/reset-password**
```json
// Request
{
  "identifier": "owner@hostel.com",
  "otp": "123456",
  "new_password": "NewPass@9999",
  "confirm_password": "NewPass@9999"
}
```

**POST /api/auth/change-password** *(requires Bearer token)*
```json
{
  "old_password": "Owner@1234",
  "new_password": "NewPass@9999",
  "confirm_password": "NewPass@9999"
}
```

**POST /api/auth/refresh-token**
```json
{ "refresh_token": "abc123..." }
```

---

## 9. Security Architecture

```
Client
  │
  │  HTTPS (TLS)
  ▼
FastAPI
  │
  ├── Bearer Token (JWT) ──► decode_token() ──► get_current_user()
  │                                                    │
  │                                              DB lookup (users)
  │
  ├── Password ──► BCrypt verify ──► hash stored in DB
  │
  ├── Refresh Token ──► SHA-256 hash ──► stored in refresh_tokens
  │
  └── OTP ──► 6-digit, 10min TTL, 5 attempts max ──► stored in otp_requests
```

**Token Lifecycle:**
```
Login → Access Token (30min) + Refresh Token (7 days)
         │
         │ Access Token expires
         ▼
      Refresh Token → New Access Token + New Refresh Token (rotation)
         │
         │ Logout / Password Change / Reset
         ▼
      All Refresh Tokens revoked → Force re-login
```

---

## 10. Setup & Running

### Prerequisites

| Tool           | Version  | Install                                      |
|----------------|----------|----------------------------------------------|
| Docker Desktop | Latest   | https://www.docker.com/products/docker-desktop |
| Python         | 3.11+    | https://www.python.org/downloads/ (local dev only) |

No MongoDB installation required — it runs as a Docker container.

---

### Option A — Docker (Recommended)

**Step 1: Install Docker Desktop**

1. Download from https://www.docker.com/products/docker-desktop
2. Install and start Docker Desktop
3. Verify:
```bash
docker --version
docker compose version
```

**Step 2: Configure secrets (optional)**

Edit `.env.docker` to change passwords and JWT secret before first run:
```env
MONGO_ROOT_PASSWORD=your-strong-password
JWT_SECRET=your-very-long-random-secret
DEFAULT_OWNER_PASSWORD=YourOwnerPass@123
```

Generate a strong JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

**Step 3: Build and start everything**

```bash
docker compose up --build
```

This will:
1. Pull MongoDB 7.0 image
2. Build the API and migrator images
3. Start MongoDB and wait for it to be healthy
4. Run all migrations (V1 → V2 → V3) — creates indexes, roles, permissions, default owner
5. Start the API server

Expected output (condensed):
```
hostel_mongo     | MongoDB starting...
hostel_mongo     | Waiting for connections on port 27017
hostel_migrator  | Waiting for MongoDB at mongodb://admin:...@mongo:27017 ...
hostel_migrator  | MongoDB is ready.
hostel_migrator  | Applying V1__create_indexes ...
hostel_migrator  |   [V1] Indexes created
hostel_migrator  | ✓ V1__create_indexes applied
hostel_migrator  | Applying V2__seed_roles_and_permissions ...
hostel_migrator  |   [V2] 6 roles, 26 permissions seeded
hostel_migrator  | ✓ V2__seed_roles_and_permissions applied
hostel_migrator  | Applying V3__seed_default_owner ...
hostel_migrator  |   [V3] Default owner created: owner@hostel.com / Owner@1234
hostel_migrator  | ✓ V3__seed_default_owner applied
hostel_migrator  | All migrations applied successfully.
hostel_api       | INFO: Uvicorn running on http://0.0.0.0:8000
```

**Step 4: Access the API**

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

### Useful Docker Commands

```bash
# Start in background
docker compose up -d --build

# View logs
docker compose logs -f
docker compose logs -f api
docker compose logs migrator

# Stop everything
docker compose down

# Stop and delete all data (wipes MongoDB volume)
docker compose down -v

# Re-run migrations only (e.g. after adding a new V4 file)
docker compose up migrator

# Rebuild only the API image (after code changes)
docker compose up --build api

# Open MongoDB shell inside the container
docker exec -it hostel_mongo mongosh -u admin -p secret123 --authenticationDatabase admin
```

---

### Option B — Local Development (No Docker)

Use this when you want hot-reload during development.

**Step 1: Install Python 3.11+**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Step 2: Start MongoDB via Docker (just the DB)**

```bash
docker compose up -d mongo
```

Or install MongoDB locally from https://www.mongodb.com/try/download/community

**Step 3: Run migrations**

```bash
python -m app.migrations.migrator
```

**Step 4: Start the API**

```bash
uvicorn app.main:app --reload
```

The `.env` file points to `localhost:27017` (no auth) for local dev.
If using the Docker mongo container locally, update `.env`:
```env
MONGO_URI=mongodb://admin:secret123@localhost:27017/hostel_management?authSource=admin
```

---

## 11. Testing the APIs

### Option A — Swagger UI (Recommended for quick testing)

1. Open http://localhost:8000/docs
2. Use the **POST /api/auth/login** endpoint with:
   ```json
   { "identifier": "owner@hostel.com", "password": "Owner@1234" }
   ```
3. Copy the `access_token` from the response
4. Click **Authorize** (top right) → paste `Bearer <access_token>`
5. Now test protected endpoints like `GET /api/users/me`

---

### Option B — curl

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"identifier\": \"owner@hostel.com\", \"password\": \"Owner@1234\"}"
```

**Get current user (replace TOKEN):**
```bash
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer TOKEN"
```

**Forgot Password:**
```bash
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d "{\"identifier\": \"owner@hostel.com\"}"
```
> Check the terminal running uvicorn for the OTP printed as `[DEV] OTP for ...`

**Verify OTP:**
```bash
curl -X POST http://localhost:8000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d "{\"identifier\": \"owner@hostel.com\", \"otp\": \"XXXXXX\", \"purpose\": \"forgot_password\"}"
```

**Reset Password:**
```bash
curl -X POST http://localhost:8000/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d "{\"identifier\": \"owner@hostel.com\", \"otp\": \"XXXXXX\", \"new_password\": \"NewPass@9999\", \"confirm_password\": \"NewPass@9999\"}"
```

**Refresh Token:**
```bash
curl -X POST http://localhost:8000/api/auth/refresh-token \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"YOUR_REFRESH_TOKEN\"}"
```

**Logout:**
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"YOUR_REFRESH_TOKEN\"}"
```

---

### Option C — Postman

1. Import the base URL: `http://localhost:8000`
2. Create a collection with the endpoints above
3. Set `Authorization: Bearer {{access_token}}` as a collection variable
4. After login, set `access_token` variable from the response

---

### Test Scenarios Checklist

| Scenario                                  | Expected Result                        |
|-------------------------------------------|----------------------------------------|
| Login with valid credentials              | 200 + tokens                           |
| Login with wrong password                 | 401 Invalid username or password       |
| Login 5 times with wrong password         | 403 Account locked                     |
| Login with locked account                 | 403 Account is locked                  |
| Login with inactive user                  | 403 Account is inactive                |
| Access protected route without token      | 403 Not authenticated                  |
| Access protected route with expired token | 401 Invalid or expired token           |
| Refresh with valid refresh token          | 200 + new tokens                       |
| Refresh with revoked token                | 401 Invalid or revoked refresh token   |
| Forgot password → OTP in console          | 200 + OTP printed to terminal          |
| Verify correct OTP                        | 200 OTP verified                       |
| Verify expired OTP                        | 400 OTP has expired                    |
| Verify wrong OTP 5 times                  | 400 Maximum OTP attempts exceeded      |
| Reset password with weak password         | 422 Validation error                   |
| Reset password reusing old password       | 400 Cannot reuse last 5 passwords      |
| Change password with wrong old password   | 400 Old password is incorrect          |

---

## 12. Future Enhancements

| Feature                        | Notes                                                    |
|--------------------------------|----------------------------------------------------------|
| Email/SMS OTP delivery         | Integrate AWS SNS, Twilio, or SendGrid in `otp_service.py` |
| Email verification flow        | Use `email_verification` OTP purpose                     |
| Mobile verification flow       | Use `mobile_verification` OTP purpose                    |
| Password expiry policy         | Add `password_expires_at` to users collection            |
| Two-Factor Authentication      | Add TOTP (Google Authenticator) support                  |
| Admin user management API      | Create/update/deactivate users                           |
| TenantId isolation             | Add `tenant_id` to all business collections              |
| Rate limiting                  | Add `slowapi` middleware for brute-force protection      |
| HTTPS enforcement              | Configure TLS in production (nginx/ALB)                  |
| Token blacklist                | Redis-based blacklist for immediate access token revocation |
