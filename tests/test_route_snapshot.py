"""Guard against accidental route changes.

The snapshot lists every registered route as "path | METHODS". If you add,
remove, or rename an endpoint on purpose, regenerate the snapshot:

    python3 tests/test_route_snapshot.py > tests/route_snapshot.txt
"""

import os


def flatten_routes(app):
    out = []

    def walk(routes):
        for r in routes:
            if type(r).__name__ == "_IncludedRouter":
                walk(r.original_router.routes)
                continue
            path = getattr(r, "path", None)
            methods = getattr(r, "methods", None)
            if path is not None:
                out.append(f"{path} | {','.join(sorted(methods)) if methods else '-'}")
            sub = getattr(r, "routes", None)
            if sub:
                walk(sub)

    walk(app.routes)
    return sorted(out)


def test_route_table_matches_snapshot(app):
    snapshot_path = os.path.join(os.path.dirname(__file__), "route_snapshot.txt")
    with open(snapshot_path, "r", encoding="utf-8") as f:
        expected = [line for line in f.read().splitlines() if line.strip()]

    actual = flatten_routes(app)
    assert actual == expected, (
        "Registered routes differ from tests/route_snapshot.txt. "
        "If this change is intentional, regenerate the snapshot (see module docstring)."
    )


if __name__ == "__main__":
    import conftest  # noqa: F401  (sets env + sys.path)
    from backend.server import create_app

    for line in flatten_routes(create_app()):
        print(line)
