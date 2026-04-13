import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone

try:
    import psycopg
    from psycopg import sql
except Exception:
    psycopg = None
    sql = None

_ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from app.storage import db_tables
from utils.databaseStorage import _PostgresConnectionWrapper

TABLE_ORDER = [
    "admins",
    "students",
    "students_sheet_map",
    "student_auth",
    "bot_users",
    "teachers",
    "app_meta",
    "resource_types",
    "resources",
    "subject_summaries",
    "lesson_catalog",
    "chat_messages",
    "chat_blocked_users",
    "resource_comments",
]


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate data from local SQLite to PostgreSQL."
    )
    parser.add_argument(
        "--sqlite-path",
        default=os.path.join("utils", "app_data.sqlite3"),
        help="Path to source SQLite database file.",
    )
    parser.add_argument(
        "--postgres-url",
        default=os.environ.get("DATABASE_URL", "").strip(),
        help="Target PostgreSQL connection URL. Defaults to env DATABASE_URL.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Rows per batch for each insert/upsert.",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Truncate target tables before importing data.",
    )
    parser.add_argument(
        "--tables",
        default="",
        help="Optional comma-separated table list to migrate.",
    )
    return parser.parse_args()


def quote_sqlite_ident(identifier):
    return '"' + str(identifier).replace('"', '""') + '"'


def ensure_postgres_schema(pg_conn):
    conn = _PostgresConnectionWrapper(pg_conn)
    db_tables.create_tables(conn)
    db_tables.ensure_admins_schema(conn)
    db_tables.ensure_students_schema(conn)
    db_tables.ensure_students_sheet_map_schema(conn)
    db_tables.ensure_lesson_catalog_schema(conn)
    db_tables.ensure_subject_summaries_schema(conn)
    db_tables.ensure_resources_schema(conn)
    db_tables.ensure_resource_comments_schema(conn)
    db_tables.ensure_chat_schema(conn)
    conn.commit()


def list_sqlite_tables(sqlite_conn):
    rows = sqlite_conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row["name"]) for row in rows]


def list_postgres_tables(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = current_schema()
            ORDER BY tablename
            """
        )
        rows = cur.fetchall()
    return [str(row[0]) for row in rows]


def get_sqlite_columns(sqlite_conn, table_name):
    rows = sqlite_conn.execute(
        f"PRAGMA table_info({quote_sqlite_ident(table_name)})"
    ).fetchall()
    return [str(row["name"]) for row in rows]


def get_postgres_columns(pg_conn, table_name):
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        rows = cur.fetchall()
    return [str(row[0]) for row in rows]


def get_primary_key_columns(pg_conn, table_name):
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_class c ON c.oid = i.indrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
            WHERE n.nspname = current_schema()
              AND c.relname = %s
              AND i.indisprimary
            ORDER BY k.ord
            """,
            (table_name,),
        )
        rows = cur.fetchall()
    return [str(row[0]) for row in rows]


def iter_sqlite_rows(sqlite_conn, table_name, columns, batch_size):
    if not columns:
        return
    quoted_columns = ", ".join(quote_sqlite_ident(col) for col in columns)
    table_ident = quote_sqlite_ident(table_name)
    cursor = sqlite_conn.execute(
        f"SELECT {quoted_columns} FROM {table_ident}"
    )
    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        yield batch


def build_upsert_statement(table_name, columns, pk_columns):
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(sql.Identifier(col) for col in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    if not pk_columns:
        return statement

    non_pk_columns = [col for col in columns if col not in set(pk_columns)]
    if not non_pk_columns:
        return statement + sql.SQL(" ON CONFLICT ({}) DO NOTHING").format(
            sql.SQL(", ").join(sql.Identifier(col) for col in pk_columns)
        )

    updates = sql.SQL(", ").join(
        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
        for col in non_pk_columns
    )
    return statement + sql.SQL(" ON CONFLICT ({}) DO UPDATE SET {}").format(
        sql.SQL(", ").join(sql.Identifier(col) for col in pk_columns),
        updates,
    )


def truncate_tables(pg_conn, table_names):
    if not table_names:
        return
    with pg_conn.cursor() as cur:
        cur.execute(
            sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(sql.Identifier(name) for name in table_names)
            )
        )
    pg_conn.commit()


def sync_sequences(pg_conn, table_names):
    with pg_conn.cursor() as cur:
        for table_name in table_names:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )
            columns = [str(row[0]) for row in cur.fetchall()]
            for column_name in columns:
                cur.execute(
                    "SELECT pg_get_serial_sequence(%s, %s)",
                    (table_name, column_name),
                )
                sequence_name = cur.fetchone()[0]
                if not sequence_name:
                    continue

                max_query = sql.SQL("SELECT MAX({}) FROM {}").format(
                    sql.Identifier(column_name),
                    sql.Identifier(table_name),
                )
                cur.execute(max_query)
                max_value = cur.fetchone()[0]
                if max_value is None:
                    cur.execute(
                        "SELECT setval(%s, 1, false)",
                        (sequence_name,),
                    )
                else:
                    cur.execute(
                        "SELECT setval(%s, %s, true)",
                        (sequence_name, int(max_value)),
                    )
    pg_conn.commit()


def pick_tables_to_migrate(sqlite_tables, postgres_tables, custom_tables):
    common_tables = set(sqlite_tables).intersection(set(postgres_tables))

    if custom_tables:
        requested = [name.strip() for name in custom_tables.split(",") if name.strip()]
        return [name for name in requested if name in common_tables]

    ordered = [name for name in TABLE_ORDER if name in common_tables]
    remaining = sorted(common_tables.difference(set(ordered)))
    return ordered + remaining


def migrate_table(sqlite_conn, pg_conn, table_name, batch_size):
    source_columns = get_sqlite_columns(sqlite_conn, table_name)
    target_columns = get_postgres_columns(pg_conn, table_name)
    shared_columns = [name for name in source_columns if name in set(target_columns)]

    if not shared_columns:
        print(f"[skip] {table_name}: no shared columns")
        return 0

    pk_columns = get_primary_key_columns(pg_conn, table_name)
    statement = build_upsert_statement(table_name, shared_columns, pk_columns)

    inserted_total = 0
    with pg_conn.cursor() as cur:
        for batch in iter_sqlite_rows(sqlite_conn, table_name, shared_columns, batch_size):
            cur.executemany(statement, batch)
            inserted_total += len(batch)
    pg_conn.commit()
    print(f"[ok] {table_name}: migrated {inserted_total} row(s)")
    return inserted_total


def main():
    args = parse_args()
    sqlite_path = os.path.abspath(args.sqlite_path)
    postgres_url = str(args.postgres_url or "").strip()
    batch_size = max(int(args.batch_size or 1), 1)

    if not os.path.isfile(sqlite_path):
        raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")
    if not postgres_url:
        raise RuntimeError("Missing PostgreSQL URL. Set --postgres-url or DATABASE_URL.")
    if not (
        postgres_url.startswith("postgres://")
        or postgres_url.startswith("postgresql://")
    ):
        raise RuntimeError("PostgreSQL URL must start with postgres:// or postgresql://")
    if psycopg is None or sql is None:
        raise RuntimeError(
            "Missing dependency `psycopg`. Run: pip install -r requirements.txt"
        )

    started_at = utc_now_iso()
    print(f"Migration started at {started_at}")
    print(f"SQLite source: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg.connect(postgres_url)
    pg_conn.autocommit = False

    try:
        ensure_postgres_schema(pg_conn)
        sqlite_tables = list_sqlite_tables(sqlite_conn)
        postgres_tables = list_postgres_tables(pg_conn)
        tables = pick_tables_to_migrate(sqlite_tables, postgres_tables, args.tables)

        if not tables:
            print("No matching tables to migrate.")
            return

        print("Tables:", ", ".join(tables))
        if args.truncate_target:
            print("Truncating target tables before import...")
            truncate_tables(pg_conn, tables)

        total_rows = 0
        for table_name in tables:
            total_rows += migrate_table(sqlite_conn, pg_conn, table_name, batch_size)

        sync_sequences(pg_conn, tables)
        finished_at = utc_now_iso()
        print(f"Migration finished at {finished_at}")
        print(f"Total migrated rows: {total_rows}")
    finally:
        try:
            sqlite_conn.close()
        except Exception:
            pass
        try:
            pg_conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
