# API Contract — Authentication Microservice

**Course:** Microservice-oriented Architectures (LAB 3 — Designing an API Contract)  
**Professor:** Zouheir BANOU  
**Responsible student:** Hiba OUAFI  
**Service:** Authentication (Auth)  
**Implementation:** Python, FastAPI, SQLite, JWT  
**API version:** 1.0.0  
**Base URL:** `http://localhost:8081`

## 1. Role and consumers

The Authentication microservice is responsible for customer registration, login, current-user profile retrieval, and logout. The React e-commerce frontend is an API consumer; Auth is the API provider. Data is exchanged over HTTP using JSON. Auth issues signed JWT access tokens after a successful login.

## 2. Summary of exposed operations

| Operation | HTTP method | Endpoint | Purpose | Success status |
|---|---|---|---|---|
| Register | `POST` | `/api/auth/register` | Create a customer account | `201 Created` |
| Login | `POST` | `/api/auth/login` | Verify credentials and issue a JWT | `200 OK` |
| Current user | `GET` | `/api/auth/me` | Retrieve the authenticated user's profile | `200 OK` |
| Logout | `POST` | `/api/auth/logout` | Revoke a provided valid JWT | `200 OK` |
| Health check | `GET` | `/` | Confirm that the service is running | `200 OK` |

**URL and query parameters:** None of these five endpoints uses path parameters or query parameters. User data is supplied in JSON request bodies or identified through an Authorization header.

## 3. Shared data structures

### 3.1 `User` response object

| Field | JSON type | Required | Description |
|---|---|---|---|
| `id` | string (UUID) | Yes | Generated user identifier |
| `name` | string | Yes | Customer name |
| `email` | string (email format) | Yes | Customer email address |
| `role` | string | Yes | `CUSTOMER` for newly registered accounts |

Example:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Hiba",
  "email": "hiba@example.com",
  "role": "CUSTOMER"
}
```

Passwords and password hashes are **never returned** in user responses.

### 3.2 Business/authentication error schema

```json
{
  "message": "Error description"
}
```

- `message`: required string.
- HTTP status code depends on the endpoint and error condition.

### 3.3 Request-validation error schema (`422 Unprocessable Entity`)

Invalid or missing request fields are rejected by FastAPI/Pydantic using its standard `detail` structure:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Validation error description",
      "type": "validation_error_type"
    }
  ]
}
```

`detail` is an array; each element describes a validation issue. The precise `msg` and `type` depend on the violation and FastAPI/Pydantic version.

## 4. Register a customer

**Method and endpoint:** `POST /api/auth/register`  
**Purpose:** Create a new account, hash the password with Argon2, and save the user in SQLite.  
**Required request header:** `Content-Type: application/json`  
**URL/query parameters:** None.

**Request-body schema:**

| Field | JSON type / format | Required | Rules |
|---|---|---|---|
| `name` | string | Yes | Length 1–100; whitespace-only name rejected |
| `email` | string / email | Yes | Valid email address; normalized to lowercase |
| `password` | string | Yes | Minimum 8 characters |

**Request example:**

```http
POST /api/auth/register
Content-Type: application/json
```

```json
{
  "name": "Hiba",
  "email": "hiba@example.com",
  "password": "TestAuth2026!"
}
```

**Successful response — `201 Created`:** body is a `User` object.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Hiba",
  "email": "hiba@example.com",
  "role": "CUSTOMER"
}
```

**Errors:**

| HTTP status | Condition | Response schema / example |
|---|---|---|
| `400 Bad Request` | Name is empty after whitespace trimming | `{"message":"Name is required"}` |
| `409 Conflict` | Email is already registered | `{"message":"Email already registered"}` |
| `422 Unprocessable Entity` | Missing field, invalid email, name length, or password length | FastAPI validation error (`detail` array) |

## 5. Login

**Method and endpoint:** `POST /api/auth/login`  
**Purpose:** Verify a customer's email and password, then issue a signed JWT (HS256; expires after 8 hours).  
**Required request header:** `Content-Type: application/json`  
**URL/query parameters:** None.

**Request-body schema:**

| Field | JSON type / format | Required | Rules |
|---|---|---|---|
| `email` | string / email | Yes | Valid email address |
| `password` | string | Yes | Compared with the stored password hash |

**Request example:**

```http
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "hiba@example.com",
  "password": "TestAuth2026!"
}
```

**Successful response — `200 OK`:**

| Field | JSON type | Required | Description |
|---|---|---|---|
| `user` | object (`User`) | Yes | Authenticated user profile |
| `token` | string | Yes | Signed JWT bearer token |

```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Hiba",
    "email": "hiba@example.com",
    "role": "CUSTOMER"
  },
  "token": "<signed-jwt-token>"
}
```

**Errors:**

| HTTP status | Condition | Response schema / example |
|---|---|---|
| `401 Unauthorized` | Unknown email or incorrect password | `{"message":"Invalid email or password"}` |
| `422 Unprocessable Entity` | Missing or invalid request fields | FastAPI validation error (`detail` array) |

## 6. Retrieve the current user

**Method and endpoint:** `GET /api/auth/me`  
**Purpose:** Identify the user associated with a valid, non-revoked JWT.  
**Required request header:** `Authorization: Bearer <jwt-token>`  
**Content-Type:** Not required because this request has no body.  
**URL/query parameters:** None.  
**Request body:** None.

**Request example:**

```http
GET /api/auth/me
Authorization: Bearer <jwt-token>
```

**Successful response — `200 OK`:** body is a `User` object.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Hiba",
  "email": "hiba@example.com",
  "role": "CUSTOMER"
}
```

**Errors:**

| HTTP status | Condition | Response schema / example |
|---|---|---|
| `401 Unauthorized` | No bearer token provided | `{"message":"Authentication required"}` |
| `401 Unauthorized` | Invalid or expired token | `{"message":"Invalid or expired token"}` |
| `401 Unauthorized` | Token was revoked | `{"message":"Token has been revoked"}` |
| `401 Unauthorized` | User associated with token no longer exists | `{"message":"User not found"}` |

## 7. Logout

**Method and endpoint:** `POST /api/auth/logout`  
**Purpose:** Revoke the identifier (`jti`) of a supplied valid JWT, preventing its future use in `/api/auth/me`.  
**Request header for authenticated logout:** `Authorization: Bearer <jwt-token>`  
**Content-Type:** Not required because this request has no body.  
**URL/query parameters:** None.  
**Request body:** None.

**Request example:**

```http
POST /api/auth/logout
Authorization: Bearer <jwt-token>
```

**Successful response — `200 OK`:**

| Field | JSON type | Required | Value |
|---|---|---|---|
| `success` | boolean | Yes | `true` |

```json
{
  "success": true
}
```

**Current implementation and error behavior:** This endpoint also responds with `200 OK` and `{"success":true}` when the token is missing or invalid. A valid supplied token is added to the revoked-token store. The endpoint does not currently return a distinct HTTP error status for these cases.

## 8. Service health check

**Method and endpoint:** `GET /`  
**Purpose:** Report that the Authentication service is running.  
**Required headers:** None.  
**Content-Type:** Not required; no request body.  
**URL/query parameters:** None.  
**Request body:** None.

**Successful response — `200 OK`:**

| Field | JSON type | Required |
|---|---|---|
| `service` | string | Yes |
| `status` | string | Yes |
| `port` | integer | Yes |

```json
{
  "service": "MSOA Authentication Service",
  "status": "running",
  "port": 8081
}
```

## 9. API contract compatibility

The React frontend depends on the endpoints and response structures above, especially `user` and `token` in the login response. Renaming fields, changing their types, changing endpoints, or replacing JSON bodies without coordinating with consumers would be a breaking change. The contract documents the existing Auth implementation; it does not introduce new endpoints or modify the service.
