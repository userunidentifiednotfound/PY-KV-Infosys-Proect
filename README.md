# Valut Sync Distributed Key-Value Store and Library Management System

## 1. Project Overview

This project is a full-stack FastAPI application that combines:

- a secure in-memory key-value store
- LRU cache behavior
- TTL-based expiration
- write-ahead logging (WAL)
- primary-to-replica synchronization
- a replica monitoring dashboard
- a bright, real-time Library Management System

The system is designed to demonstrate both backend systems concepts and polished frontend dashboards in a single project.

At a high level, the project has two application modes:

1. **Primary Server**
   - Handles authentication
   - Accepts key-value operations
   - Maintains the main in-memory store
   - Writes every change to WAL
   - Pushes updates to the replica
   - Hosts the main dashboard and the library application

2. **Replica Server**
   - Receives replicated operations from the primary
   - Maintains its own copy of replicated data
   - Measures lag and sync activity
   - Hosts a dedicated monitoring dashboard on port `9000`

---

## 2. Main Objectives of the Project

The project was built to demonstrate:

- secure API access with JWT login
- in-memory key-value storage
- least recently used cache replacement
- time-to-live expiry support
- durability concepts using write-ahead logging
- replication between a primary and replica service
- operational dashboards for monitoring
- a separate real-time business application built on the same stack

This makes the project suitable for:

- academic submission
- mini project / capstone demonstration
- distributed systems demo
- backend + frontend portfolio project

---

## 3. Core Features

### 3.1 Secure Authentication

- User login is handled by FastAPI.
- JWT tokens are generated after successful authentication.
- Protected routes require the token.
- Current default credentials:
  - `username: admin`
  - `password: admin123`

### 3.2 In-Memory Key-Value Store

The primary server supports:

- `SET` key
- `GET` key
- `DELETE` key

Each value is stored in memory for fast access.

### 3.3 TTL Support

Keys can be created with an optional TTL.

- If TTL is provided, the key receives an expiry timestamp.
- A background cleanup task removes expired keys automatically.

### 3.4 LRU Cache Logic

The store has a maximum capacity.

- When capacity is full and a new key is inserted:
  - the least recently used key is removed
- `GET` operations refresh access order
- the dashboard shows current key order visually

### 3.5 Write-Ahead Log (WAL)

All mutating operations are recorded in `wal.log`.

This log supports:

- durability of operations
- replay during startup
- manual inspection from the dashboard
- compaction to reduce log growth

### 3.6 Replication

When the primary server changes data:

- the operation is written to WAL
- the operation is sent to the replica server
- the replica applies the same operation

Replica status includes:

- online / offline state
- applied operations
- last sync time
- key counts
- replica lag information

### 3.7 Replica Dashboard

The replica server includes a dedicated UI for:

- recent replication logs
- key count trend chart
- lag display
- local test CLI
- replica snapshot view

### 3.8 Valut Sync Library

The project also includes a second working application:

- book inventory management
- add, edit, delete books
- borrow and return operations
- borrower tracking
- live stats
- search and filtering
- persistent data in `library_data.json`

This page uses the same design concept as the dashboard but with brighter, more vibrant professional colors.

---

## 4. Technology Stack

### Backend

- Python
- FastAPI
- Pydantic
- JWT (`python-jose`)
- AsyncIO

### Frontend

- HTML
- CSS
- JavaScript
- Chart.js
- Boxicons

### Data / Storage

- In-memory Python structures
- `wal.log` for write-ahead logging
- `library_data.json` for library persistence

---

## 5. Project Structure

```text
e:\infosys
├── main.py              # Primary FastAPI server
├── replica.py           # Replica FastAPI server + replica dashboard UI
├── index.html           # Main dashboard page
├── app.js               # Main dashboard frontend logic
├── style.css            # Main dashboard styling
├── library.html         # Library Management System page
├── library.js           # Library frontend logic
├── library.css          # Library styling
├── wal.log              # Write-ahead log
├── library_data.json    # Persistent library data
├── bg1.jpg              # Shared background image
└── README2.md           # Full project documentation
```

---

## 6. How the Project Works End-to-End

## 6.1 Primary Key-Value Flow

1. User logs into the main dashboard.
2. User performs `SET`, `GET`, or `DELETE`.
3. The primary server validates the JWT token.
4. If it is a write operation:
   - the change is written to `wal.log`
   - the store is updated in memory
   - the operation is sent to the replica server
5. The dashboard refreshes:
   - LRU state
   - WAL information
   - replication state

## 6.2 WAL Replay Flow

1. Primary server starts.
2. `replay_wal()` reads the WAL file.
3. Each valid operation is re-applied to rebuild the in-memory store.
4. This simulates recovery after restart.

## 6.3 Replication Flow

1. Primary server writes an operation with a timestamp.
2. Operation is posted to `http://127.0.0.1:9000/replica/apply`
3. Replica stores the same change.
4. Replica dashboard records:
   - time
   - operation type
   - key
   - lag
5. Main dashboard can query replica metrics through `/admin/replica-status`

## 6.4 Library Flow

1. User opens the `Library Management System` page from the main dashboard.
2. The page fetches `/api/library/books`
3. Book cards, stats, and feed are rendered
4. User can:
   - add a book
   - edit a book
   - borrow a copy
   - return a copy
   - delete a book
5. Data is saved to `library_data.json`
6. The page auto-refreshes every 3 seconds for a real-time feel

---

## 7. Important Backend Components

### 7.1 Authentication

Implemented in `main.py`.

Main functions:

- `authenticate_user()`
- `create_access_token()`
- `get_current_user()`

Purpose:

- verifies credentials
- issues JWT token
- protects private routes

### 7.2 WAL Logic

Important functions in `main.py`:

- `write_wal()`
- `replay_wal()`
- `compact_wal()`

Purpose:

- record all writes
- recover state after restart
- reduce log size using compaction

### 7.3 Expiry Cleanup

Background task:

- `expiry_cleanup()`

Purpose:

- remove expired keys every few seconds

### 7.4 Replica Monitoring

Important endpoints:

- `/admin/replica-status`
- `/admin/sync`

Purpose:

- inspect replica health
- compare primary and replica state
- force sync from WAL to replica

### 7.5 Library Data Layer

Important functions:

- `load_library_data()`
- `save_library_data()`
- `compute_library_stats()`
- `find_library_book()`

Purpose:

- persist library records
- generate summary statistics
- support live inventory operations

---

## 8. Frontend Pages

## 8.1 Main Dashboard

File: `index.html`

Purpose:

- login to the system
- manage key-value store
- inspect server health
- view LRU cache
- inspect WAL data
- monitor replica status
- open the library application

Main frontend logic:

- `app.js`

## 8.2 Replica Dashboard

Served directly from:

- `replica.py`

Purpose:

- visualize replica telemetry
- show lag and sync logs
- observe key count trend
- test replica-local CLI commands

## 8.3 Library Management System

Files:

- `library.html`
- `library.js`
- `library.css`

Purpose:

- manage books and circulation
- show real-time updates
- provide a business application built on top of the project

---

## 9. API Summary

## 9.1 Authentication

- `POST /auth/login`
- `GET /auth/me`

## 9.2 Key-Value APIs

- `POST /kv`
- `GET /kv/{key}`
- `DELETE /kv/{key}`

## 9.3 Admin / Monitoring APIs

- `GET /health`
- `GET /admin/store`
- `GET /admin/wal-status`
- `POST /admin/compact`
- `GET /admin/replica-status`
- `POST /admin/sync`

## 9.4 Replica APIs

- `GET /health` on replica server
- `POST /replica/apply`
- `GET /metrics`

## 9.5 Library APIs

- `GET /api/library/books`
- `POST /api/library/books`
- `PATCH /api/library/books/{book_id}`
- `POST /api/library/books/{book_id}/borrow`
- `POST /api/library/books/{book_id}/return`
- `DELETE /api/library/books/{book_id}`

---

## 10. Steps to Run the Project

## 10.1 Install Dependencies

Create and activate a virtual environment if needed, then install:

```bash
pip install fastapi uvicorn python-jose[cryptography] python-multipart requests
```

If you already use the included `.venv`, activate it first.

## 10.2 Start the Primary Server

Run:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## 10.3 Start the Replica Server

In another terminal:

```bash
uvicorn replica:app --reload --host 127.0.0.1 --port 9000
```

## 10.4 Open the Application

Main dashboard:

```text
http://127.0.0.1:8000
```

Replica dashboard:

```text
http://127.0.0.1:9000
```

Library Management System:

```text
http://127.0.0.1:8000/library
```

## 10.5 Login

Use:

```text
username: admin
password: admin123
```

---

## 11. Step-by-Step Demo Guide

If you want to demonstrate the project clearly during evaluation, use this sequence:

### Step 1

Start both servers on ports `8000` and `9000`.

### Step 2

Open the main dashboard and login.

### Step 3

Show the health check and explain that the primary server is running.

### Step 4

Add a few key-value pairs using:

- Set Key form
- CLI simulation

### Step 5

Show LRU ordering by inserting more keys than capacity.

Explain:

- oldest key gets evicted
- newest key remains

### Step 6

Show WAL status.

Explain:

- every write is logged
- WAL allows recovery
- compaction reduces file size

### Step 7

Open replica dashboard on port `9000`.

Show:

- replica is online
- logs are updating
- lag is being measured
- key count chart changes in real time

### Step 8

Return to main dashboard and show replication status.

Explain:

- main server checks replica metrics
- sync state is visible from the primary UI

### Step 9

Open the Library Management System.

Show:

- add a new book
- borrow a copy
- return a copy
- edit metadata
- delete a book
- live stats update automatically

### Step 10

Explain persistence:

- key-value durability uses WAL
- library data persists in `library_data.json`

---

## 12. Design and UI Notes

The project uses a consistent visual identity:

- `bg1.jpg` as the shared atmospheric background
- glass-style cards
- neon/cyan accents in the core dashboards
- brighter coral/aqua/gold/violet palette in the library page

This gives the project both:

- technical credibility
- polished presentation value

---

## 13. Strengths of the Project

- Combines backend systems concepts and real UI
- Demonstrates recovery and replication ideas
- Includes authentication and protected routes
- Contains two working frontends:
  - systems dashboard
  - business application
- Real-time feel through live refresh
- Persistent storage for library records

---

## 14. Current Limitations

- Replica synchronization is HTTP-based polling / push, not websocket-based
- Only one built-in user is currently configured
- Key-value data is mainly memory-based except WAL recovery
- Replica conflict handling is minimal
- Library real-time updates use periodic refresh, not server push

These are acceptable for a mini project and also provide clear future enhancement ideas.

---

## 15. Future Improvements

Possible next upgrades:

1. Add multi-user registration and role-based access
2. Add due dates and overdue alerts in library
3. Add book cover uploads
4. Add audit history for library actions
5. Replace polling with WebSockets for real-time updates
6. Add database support using SQLite or PostgreSQL
7. Add charts for WAL growth and replica lag trends in main dashboard
8. Add export and reporting features for library data

---

## 16. Conclusion

This project is more than a basic CRUD application. It demonstrates:

- secure authentication
- in-memory systems design
- log-based recovery
- replication concepts
- monitoring dashboards
- and an additional real-time Library Management System

It can be presented as a strong mini project because it shows both:

- systems-level backend thinking
- user-facing application design

---

## 17. Quick Start Summary

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
uvicorn replica:app --reload --host 127.0.0.1 --port 9000
```

Then open:

```text
Main Dashboard:    http://127.0.0.1:8000
Replica Dashboard: http://127.0.0.1:9000
Library System:    http://127.0.0.1:8000/library
```

Login with:

```text
admin / admin123
```
