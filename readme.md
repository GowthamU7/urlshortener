# 🔗 Scalable URL Shortener

A production-style URL shortening service inspired by Bitly, built with **FastAPI, PostgreSQL, Redis, and Docker**.

The system demonstrates backend engineering concepts such as **caching, rate limiting, analytics tracking, background processing, and scalable system design**.

---

# 🚀 Features

### URL Shortening
Convert long URLs into short shareable links.

Example:

https://example.com/articles/very-long-url


becomes


https://short.ly/abc123


Supports:

- Custom aliases
- Expiring links
- Deterministic Base62 short codes

---

### ⚡ Fast Redirects with Redis

The redirect endpoint follows a **cache-aside pattern**.

1. Check Redis cache
2. If cache hit → redirect immediately
3. If cache miss → query PostgreSQL
4. Cache the mapping
5. Redirect

This reduces database load and improves latency.

---

### 📊 Click Analytics

Each redirect logs detailed analytics including:

- timestamp
- IP address
- user agent
- referrer

The system stores:

**Summary metrics**


---

### 🔄 Background Processing

Click-event logging runs in a **FastAPI background task**.

This ensures:

- redirect response stays fast
- analytics writes do not block user requests

---

### 🛡 Rate Limiting

Redis counters protect the API from abuse.

Example limits:

| Endpoint | Limit |
|--------|------|
POST `/shorten` | 5 requests / minute |
GET `/short_code` | 20 requests / minute |

---

### 🔢 Base62 Short Code Generation

Short codes are generated using Base62 encoding of database IDs.

Characters used:
    0-9
    a-z
    A-Z
  

Example conversions:

| ID | Short Code |
|----|-----------|
1 | 1 |
62 | 10 |
125 | cb |

Benefits:

- deterministic generation
- no collision loops
- compact URLs

---

# 🏗 Architecture

```mermaid
flowchart LR
    U[User / Client] --> A[FastAPI API]

    A -->|POST /shorten| RL1[Redis Rate Limit Check]
    A -->|GET /{short_code}| RL2[Redis Rate Limit Check]

    RL1 --> DB[(PostgreSQL)]
    RL2 --> C[(Redis Cache)]

    C -->|Cache hit| R[Redirect to Original URL]
    C -->|Cache miss| DB
    DB -->|URL mapping| A
    A -->|Cache mapping| C
    A --> R

    A -->|Increment click_count| DB
    A -->|Background task| CE[Click Event Logger]
    CE --> DB

    A -->|GET /analytics/{short_code}| DB