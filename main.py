from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field
import asyncio
import time
import json
import os
from typing import Dict, List, Optional
from collections import OrderedDict


app = FastAPI(
    title="PyKV - Secure In-Memory Key-Value Store",
    version="4.1.0"
)

# =============================
# CONFIG
# =============================
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600
WAL_FILE = "wal.log"

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
MAX_CAPACITY = 5
store: OrderedDict[str, Dict[str, Optional[float]]] = OrderedDict()
lock = asyncio.Lock()

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
    with open(WAL_FILE, "a") as f:
        f.write(json.dumps(operation) + "\n")
        f.flush()
        os.fsync(f.fileno())

def replay_wal():
    if not os.path.exists(WAL_FILE):
        return

    with open(WAL_FILE, "r") as f:
        for line in f:
            operation = json.loads(line.strip())

            if operation["type"] == "SET":
                store[operation["key"]] = {
                    "value": operation["value"],
                    "expiry": operation["expiry"]
                }

            elif operation["type"] == "DELETE":
                store.pop(operation["key"], None)

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

@app.on_event("startup")
async def startup_event():
    replay_wal()
    asyncio.create_task(expiry_cleanup())

# Serve frontend
app.mount("/static", StaticFiles(directory="."), name="static")

# =============================
# ROUTES
# =============================

@app.get("/")
async def root():
    return FileResponse("index.html")

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
            "expiry": expiry_time
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
        write_wal({"type": "DELETE", "key": key})

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