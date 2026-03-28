from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field
import asyncio
import time
import json
import requests
import os
import uuid
from typing import Dict, List, Optional
from collections import OrderedDict
REPLICA_URL = "http://127.0.0.1:9000/replica/apply"
IS_PRIMARY = True   # Secondary → False

app = FastAPI(
    title="Valut Sync - Secure In-Memory Key-Value Store",
    version="4.1.0"
)

# =============================
# CONFIG
# =============================
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600
WAL_FILE = "wal.log"
REPLICA_HEALTH_URL = "http://127.0.0.1:9000/health"
REPLICA_METRICS_URL = "http://127.0.0.1:9000/metrics"
LIBRARY_FILE = "library_data.json"

# =============================
# USER DB
# =============================
fake_users_db = {
    "admin": {
        "username": "admin",
        "password": "admin123",
        "full_name": "Administrator",
        "email": "admin@example.com",
        "roles": ["admin", "user"],
        "preferences": {"theme": "dark", "notifications": True},
        "recent_activity": []
    }
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# =============================
# STORE (LRU)
# =============================
MAX_CAPACITY = 3    
store: OrderedDict[str, Dict[str, Optional[float]]] = OrderedDict()
lock = asyncio.Lock()
library_lock = asyncio.Lock()
library_books: List[Dict[str, object]] = []

# =============================
# PYDANTIC MODELS
# =============================

class Item(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    value: str = Field(..., min_length=1)
    ttl: Optional[int] = Field(default=None, ge=1)

    class Config:
        schema_extra = {
            "example": {
                "key": "session_token",
                "value": "abc123xyz",
                "ttl": 60
            }
        }

class KVResponse(BaseModel):
    message: str
    key: Optional[str] = None
    value: Optional[str] = None

class LRUStatus(BaseModel):
    capacity: int
    current_size: int
    keys_in_order: List[str]

class UserPublic(BaseModel):
    username: str
    full_name: str
    email: str
    roles: List[str]

class LibraryBookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    author: str = Field(..., min_length=1, max_length=80)
    category: str = Field(..., min_length=1, max_length=60)
    copies: int = Field(..., ge=1, le=50)

class LibraryBookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    author: Optional[str] = Field(default=None, min_length=1, max_length=80)
    category: Optional[str] = Field(default=None, min_length=1, max_length=60)
    copies: Optional[int] = Field(default=None, ge=1, le=50)

class BorrowRequest(BaseModel):
    borrower: str = Field(..., min_length=1, max_length=80)

# =============================
# AUTH
# =============================

def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user or user["password"] != password:
        return None
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = time.time() + ACCESS_TOKEN_EXPIRE_SECONDS
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = fake_users_db.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# =============================
# WAL FUNCTIONS
# =============================

def write_wal(operation: dict):
    operation = operation.copy()
    operation.setdefault("timestamp", time.time())

    with open(WAL_FILE, "a") as f:
        f.write(json.dumps(operation) + "\n")
        f.flush()
        os.fsync(f.fileno())

    # 🔥 Replication logic
    if IS_PRIMARY:
        try:
            requests.post(REPLICA_URL, json=operation, timeout=1)
        except:
            pass  # replica may be down

def replay_wal():
    if not os.path.exists(WAL_FILE):
        return

    with open(WAL_FILE, "r") as f:
        for line in f:
            try:
                operation = json.loads(line.strip())
            except json.JSONDecodeError:
                continue  # skip corrupted lines

            if operation["type"] == "SET":
                store[operation["key"]] = {
                    "value": operation["value"],
                    "expiry": operation["expiry"]
                }

            elif operation["type"] == "DELETE":
                store.pop(operation["key"], None)

def compact_wal():
    temp_file = "wal_compacted.log"

    with open(temp_file, "w") as f:
        for key, data in store.items():
            entry = {
                "type": "SET",
                "key": key,
                "value": data["value"],
                "expiry": data["expiry"]
            }

            f.write(json.dumps(entry) + "\n")

    os.replace(temp_file, WAL_FILE)

def current_library_timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def save_library_data():
    payload = {
        "books": library_books,
        "updated_at": time.time()
    }

    with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def load_library_data():
    global library_books

    if not os.path.exists(LIBRARY_FILE):
        library_books = [
            {
                "id": str(uuid.uuid4()),
                "title": "Atomic Habits",
                "author": "James Clear",
                "category": "Self Growth",
                "copies": 6,
                "available": 4,
                "borrowed": 2,
                "borrowers": [
                    {"name": "Aarav", "borrowed_at": current_library_timestamp()},
                    {"name": "Ishita", "borrowed_at": current_library_timestamp()}
                ],
                "created_at": current_library_timestamp(),
                "updated_at": current_library_timestamp(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Clean Code",
                "author": "Robert C. Martin",
                "category": "Engineering",
                "copies": 5,
                "available": 5,
                "borrowed": 0,
                "borrowers": [],
                "created_at": current_library_timestamp(),
                "updated_at": current_library_timestamp(),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "The Psychology of Money",
                "author": "Morgan Housel",
                "category": "Finance",
                "copies": 4,
                "available": 3,
                "borrowed": 1,
                "borrowers": [
                    {"name": "Riya", "borrowed_at": current_library_timestamp()}
                ],
                "created_at": current_library_timestamp(),
                "updated_at": current_library_timestamp(),
            },
        ]
        save_library_data()
        return

    with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    library_books = data.get("books", [])

def compute_library_stats():
    total_titles = len(library_books)
    total_copies = sum(int(book["copies"]) for book in library_books)
    borrowed_now = sum(int(book["borrowed"]) for book in library_books)
    available_now = sum(int(book["available"]) for book in library_books)

    return {
        "titles": total_titles,
        "copies": total_copies,
        "borrowed_now": borrowed_now,
        "available_now": available_now,
        "categories": len({str(book["category"]) for book in library_books}),
        "last_updated": max((book["updated_at"] for book in library_books), default="--")
    }

def find_library_book(book_id: str):
    for book in library_books:
        if book["id"] == book_id:
            return book
    return None

async def compaction_worker():
    while True:
        await asyncio.sleep(60)  # every 60 seconds

        async with lock:
            compact_wal()
# =============================
# TTL CLEANUP
# =============================

async def expiry_cleanup():
    while True:
        await asyncio.sleep(5)

        async with lock:
            current_time = time.time()

            expired_keys = [
                key for key, data in store.items()
                if data["expiry"] and current_time > data["expiry"]
            ]

            for key in expired_keys:
                store.pop(key, None)

# =============================
# STARTUP EVENT
# =============================
@app.post("/replica/apply")
async def apply_replica(operation: dict):
    if operation["type"] == "SET":
        store[operation["key"]] = {
            "value": operation["value"],
            "expiry": operation["expiry"]
        }

    elif operation["type"] == "DELETE":
        store.pop(operation["key"], None)

    return {"status": "applied"}

@app.get("/admin/replica-status")
async def replica_status():
    try:
        health_res = requests.get(REPLICA_HEALTH_URL, timeout=1)
        metrics_res = requests.get(REPLICA_METRICS_URL, timeout=1)
        health_res.raise_for_status()
        metrics_res.raise_for_status()

        health_data = health_res.json()
        metrics_data = metrics_res.json()
        primary_keys = list(store.keys())
        replica_keys = metrics_data.get("keys_in_store", [])

        in_sync = primary_keys == replica_keys
        last_log = metrics_data.get("logs", [])

        return {
            "status": "online",
            "code": health_res.status_code,
            "primary_keys": len(primary_keys),
            "replica_keys": metrics_data.get("keys", 0),
            "primary_key_order": primary_keys,
            "replica_key_order": replica_keys,
            "applied_operations": metrics_data.get("applied_operations", 0),
            "last_sync": metrics_data.get("last_sync"),
            "last_operation": last_log[-1] if last_log else None,
            "in_sync": in_sync,
            "health": health_data,
        }
    except requests.RequestException as exc:
        return {"status": "offline", "error": str(exc)}

@app.post("/admin/sync")
async def force_sync():
    if not os.path.exists(WAL_FILE):
        return {"message": "No WAL file found", "synced_operations": 0}

    synced_operations = 0
    errors = []

    with open(WAL_FILE, "r") as f:
        for line_number, line in enumerate(f, start=1):
            try:
                operation = json.loads(line.strip())
            except json.JSONDecodeError:
                errors.append(f"Skipped invalid WAL entry at line {line_number}")
                continue

            operation.setdefault("timestamp", operation.get("time_stamp", time.time()))

            try:
                response = requests.post(REPLICA_URL, json=operation, timeout=1)
                response.raise_for_status()
                synced_operations += 1
            except requests.RequestException as exc:
                errors.append(f"Line {line_number}: {exc}")

    return {
        "message": "Replica sync completed" if synced_operations else "Replica sync attempted",
        "synced_operations": synced_operations,
        "errors": errors,
    }

@app.get("/admin/benchmark")
async def benchmark():

    import time

    # Dict test
    d = {}
    start = time.time()
    for i in range(10000):
        d[str(i)] = i
    dict_time = time.time() - start

    # PyKV simulated
    start = time.time()
    for i in range(1000):
        store[str(i)] = {"value": i, "expiry": None}
    pykv_time = time.time() - start

    return {
        "dict_time": dict_time,
        "pykv_time": pykv_time
    }
@app.on_event("startup")
async def startup_event():
    replay_wal()
    load_library_data()
    asyncio.create_task(expiry_cleanup())
    asyncio.create_task(compaction_worker())
# Serve frontend
app.mount("/static", StaticFiles(directory="."), name="static")

# =============================
# ROUTES
# =============================
@app.get("/admin/log-status")
async def log_status():
    size = os.path.getsize(WAL_FILE) if os.path.exists(WAL_FILE) else 0

    return {
        "log_size_bytes": size,
        "keys_in_store": len(store)
    }
@app.get("/")
async def root():
    return FileResponse("index.html")

@app.get("/library")
async def library_page():
    return FileResponse("library.html")

# -----------------------------
# AUTH
# -----------------------------

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    token = create_access_token({"sub": user["username"]})

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/auth/me", response_model=UserPublic)
async def me(user: dict = Depends(get_current_user)):
    return UserPublic(
        username=user["username"],
        full_name=user["full_name"],
        email=user["email"],
        roles=user["roles"]
    )
@app.get("/admin/wal-status")
async def wal_status(user: dict = Depends(get_current_user)):

    size = os.path.getsize(WAL_FILE) if os.path.exists(WAL_FILE) else 0

    entries = 0
    if os.path.exists(WAL_FILE):
        with open(WAL_FILE) as f:
            entries = sum(1 for _ in f)

    return {
        "log_size_bytes": size,
        "entries": entries,
        "keys_in_store": len(store)
    }
@app.post("/admin/compact")
async def manual_compaction(user: dict = Depends(get_current_user)):

    async with lock:
        compact_wal()

    return {"message": "Log compaction completed"}
# -----------------------------
# HEALTH
# -----------------------------

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "total_keys": len(store)
    }

# -----------------------------
# SET KEY
# -----------------------------

@app.post("/kv", response_model=KVResponse)
async def set_key(item: Item, user: dict = Depends(get_current_user)):

    expiry_time = time.time() + item.ttl if item.ttl else None

    async with lock:

        if item.key in store:
            store.pop(item.key)

        elif len(store) >= MAX_CAPACITY:
            lru_key, _ = store.popitem(last=False)
            write_wal({"type": "DELETE", "key": lru_key})

        write_wal({
            "type": "SET",
            "key": item.key,
            "value": item.value,
            "expiry": expiry_time,
            "timestamp": time.time()
        })

        store[item.key] = {
            "value": item.value,
            "expiry": expiry_time
        }

    return KVResponse(
        message="Key stored",
        key=item.key,
        value=item.value
    )

# -----------------------------
# GET KEY
# -----------------------------

@app.get("/kv/{key}", response_model=KVResponse)
async def get_key(key: str, user: dict = Depends(get_current_user)):

    async with lock:

        if key not in store:
            raise HTTPException(status_code=404, detail="Key not found")

        data = store.pop(key)

        if data["expiry"] and time.time() > data["expiry"]:
            raise HTTPException(status_code=404, detail="Key expired")

        store[key] = data

    return KVResponse(
        message="Key fetched",
        key=key,
        value=data["value"]
    )

# -----------------------------
# DELETE KEY
# -----------------------------

@app.delete("/kv/{key}", response_model=KVResponse)
async def delete_key(key: str, user: dict = Depends(get_current_user)):

    async with lock:

        if key not in store:
            raise HTTPException(status_code=404, detail="Key not found")

        store.pop(key)
        write_wal({"type": "DELETE", "key": key, "timestamp": time.time()})

    return KVResponse(
        message="Key deleted",
        key=key
    )

# -----------------------------
# LRU STATUS
# -----------------------------

@app.get("/admin/store", response_model=LRUStatus)
async def view_store(user: dict = Depends(get_current_user)):

    return LRUStatus(
        capacity=MAX_CAPACITY,
        current_size=len(store),
        keys_in_order=list(store.keys())
    )

# -----------------------------
# LIBRARY MANAGEMENT SYSTEM
# -----------------------------

@app.get("/api/library/books")
async def list_library_books(user: dict = Depends(get_current_user)):
    async with library_lock:
        return {
            "books": library_books,
            "stats": compute_library_stats(),
            "server_time": current_library_timestamp(),
        }

@app.post("/api/library/books")
async def create_library_book(payload: LibraryBookCreate, user: dict = Depends(get_current_user)):
    async with library_lock:
        now = current_library_timestamp()
        book = {
            "id": str(uuid.uuid4()),
            "title": payload.title,
            "author": payload.author,
            "category": payload.category,
            "copies": payload.copies,
            "available": payload.copies,
            "borrowed": 0,
            "borrowers": [],
            "created_at": now,
            "updated_at": now,
        }
        library_books.insert(0, book)
        save_library_data()

        return {"message": "Book added to library", "book": book, "stats": compute_library_stats()}

@app.patch("/api/library/books/{book_id}")
async def update_library_book(book_id: str, payload: LibraryBookUpdate, user: dict = Depends(get_current_user)):
    async with library_lock:
        book = find_library_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if payload.title is not None:
            book["title"] = payload.title
        if payload.author is not None:
            book["author"] = payload.author
        if payload.category is not None:
            book["category"] = payload.category
        if payload.copies is not None:
            borrowed = int(book["borrowed"])
            if payload.copies < borrowed:
                raise HTTPException(status_code=400, detail="Copies cannot be less than current borrowed count")
            book["copies"] = payload.copies
            book["available"] = payload.copies - borrowed

        book["updated_at"] = current_library_timestamp()
        save_library_data()

        return {"message": "Book updated", "book": book, "stats": compute_library_stats()}

@app.post("/api/library/books/{book_id}/borrow")
async def borrow_library_book(book_id: str, payload: BorrowRequest, user: dict = Depends(get_current_user)):
    async with library_lock:
        book = find_library_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if int(book["available"]) <= 0:
            raise HTTPException(status_code=400, detail="No copies available right now")

        borrower_entry = {
            "name": payload.borrower,
            "borrowed_at": current_library_timestamp()
        }
        book["borrowers"].append(borrower_entry)
        book["borrowed"] = int(book["borrowed"]) + 1
        book["available"] = int(book["copies"]) - int(book["borrowed"])
        book["updated_at"] = current_library_timestamp()
        save_library_data()

        return {"message": f"{payload.borrower} borrowed {book['title']}", "book": book, "stats": compute_library_stats()}

@app.post("/api/library/books/{book_id}/return")
async def return_library_book(book_id: str, payload: BorrowRequest, user: dict = Depends(get_current_user)):
    async with library_lock:
        book = find_library_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        borrower_name = payload.borrower.strip().lower()
        borrower_index = next(
            (index for index, borrower in enumerate(book["borrowers"]) if borrower["name"].strip().lower() == borrower_name),
            None
        )

        if borrower_index is None:
            raise HTTPException(status_code=404, detail="Borrower record not found for this book")

        book["borrowers"].pop(borrower_index)
        book["borrowed"] = max(0, int(book["borrowed"]) - 1)
        book["available"] = int(book["copies"]) - int(book["borrowed"])
        book["updated_at"] = current_library_timestamp()
        save_library_data()

        return {"message": f"{payload.borrower} returned {book['title']}", "book": book, "stats": compute_library_stats()}

@app.delete("/api/library/books/{book_id}")
async def delete_library_book(book_id: str, user: dict = Depends(get_current_user)):
    async with library_lock:
        book = find_library_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        library_books.remove(book)
        save_library_data()

        return {"message": "Book removed from library", "stats": compute_library_stats()}
