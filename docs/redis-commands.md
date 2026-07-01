# Redis Useful Commands for Debugging

You can connect to the Redis container using:
```bash
docker exec -it redis_cache redis-cli
```

Once inside the `redis-cli`, you can use the following commands to debug and verify caching and rate limiting behaviors:

## 1. Viewing Cache Keys
Check all cached courses lists:
```bash
KEYS "courses:list:*"
```

Check all rate limit counters:
```bash
KEYS "ratelimit:*"
```

Check for a specific course detail cache (e.g., Course ID 5):
```bash
KEYS "course:detail:5"
```

## 2. Inspecting Cache Content
View the cached JSON data for Course 5:
```bash
GET "course:detail:5"
```

## 3. Checking Cache Expiration (TTL)
Check how many seconds are left before a cache key expires:
```bash
TTL "course:detail:5"
```
*(If it returns `-2`, the key does not exist. If `-1`, it has no expiration).*

## 4. Manual Cache Invalidation
Manually delete a specific cache key:
```bash
DEL "course:detail:5"
```

Clear the entire Redis database (Use with caution!):
```bash
FLUSHDB
```
