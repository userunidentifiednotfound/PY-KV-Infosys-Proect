import time

# Simple dict
d = {}

start = time.time()
for i in range(100000):
    d[str(i)] = i
end = time.time()

print("Dict SET Time:", end - start)


# Valut Sync API test
import requests

start = time.time()
for i in range(1000):  # keep smaller due to network
    requests.post("http://127.0.0.1:8000/kv",
                  json={"key": str(i), "value": str(i)},
                  headers={"Authorization": "Bearer YOUR_TOKEN"})
end = time.time()

print("Valut Sync SET Time:", end - start)
