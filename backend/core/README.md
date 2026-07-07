# Backend Core

Shared backend infrastructure lives here.

- `database.py` is the clean import path for DB connection helpers while the legacy `database/` package is still active.
- `security.py` owns password hashing and verification helpers.
- `config.py` owns runtime settings helpers; the root `config.py` module is now only a compatibility wrapper.
