# Backend Core

Shared backend infrastructure lives here.

- `database.py` is the clean import path for DB connection helpers while the legacy `database/` package is still active.
- `security.py` owns password hashing and verification helpers.
- `config.py` is the package import path for runtime settings helpers currently backed by the root `config.py` module.
