# Performance Notes

Target: normal operation for 100-200 parallel active users.

## Runtime Defaults

Use separate processes for web and bot in production:

```bash
python main.py web
python main.py bot
```

Recommended env starting point:

```env
WEB_LISTEN=0.0.0.0:8080
DB_POOL_MIN=2
DB_POOL_MAX=20
DB_POOL_TIMEOUT=10
GROUP_CACHE_TTL_SECONDS=600
RATING_CACHE_TTL_SECONDS=60
RATING_CACHE_MAX_ENTRIES=128
REDIS_URL=redis://...
```

Keep this rule true:

```text
DB_POOL_MAX * web_process_count < PostgreSQL max_connections
```

## Hot Paths

- Student dashboards should prefer direct internal DB dashboard payloads before
  rebuilding large datasets.
- Rating boards use a short-lived in-process leaderboard cache to avoid sorting
  the same subject repeatedly during traffic bursts.
- Admin pages should be paginated before the student count grows much further.
- Resource files should stay on R2/CDN; the backend should serve metadata and signed
  URLs, not stream large videos.

## Next Scaling Steps

1. Add pagination/search APIs for large admin tables.
2. Move shared cache keys to Redis when running more than one web process.
3. Profile slow SQL with `EXPLAIN ANALYZE` before adding indexes.
4. Load-test login, dashboard, rating board, resources, and gradebook flows.
