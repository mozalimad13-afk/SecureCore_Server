"""Scan and fix legacy/junk rows after tenant->company migration.

This script is intentionally SQLite-focused because the default dev DB is SQLite
(`server/data/securecore.db`). It is safe to run multiple times.

It supports two modes:
- Dry-run (default): prints what it *would* change.
- Apply (`--apply`): makes a timestamped backup, then applies fixes.

Fix strategy (conservative):
- Backfill missing `company_id` from the owning `users.company_id` when possible.
- For tables that can legitimately be unscoped (e.g. CSRF tokens), we leave NULLs.
- For `notifications` with a `company_id` that disagrees with the row's user,
  we correct `notifications.company_id` to match `users.company_id`.

Usage:
  PYTHONPATH=$PWD:$PYTHONPATH python scripts/scan_and_fix_company_schema.py
  PYTHONPATH=$PWD:$PYTHONPATH python scripts/scan_and_fix_company_schema.py --apply

"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "securecore.db"
BACKUP_DIR = Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True)
class Finding:
    key: str
    details: str
    count: int


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _table_columns(cur: sqlite3.Cursor, table: str) -> set[str]:
    return {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}


def _has_table(cur: sqlite3.Cursor, table: str) -> bool:
    row = cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def scan(db_path: Path) -> list[Finding]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    findings: list[Finding] = []

    def add(key: str, details: str, sql: str, params: tuple = ()):
        count = cur.execute(sql, params).fetchone()[0]
        findings.append(Finding(key=key, details=details, count=int(count)))

    # Ensure no tenant_id columns remain
    leftover = []
    for (name,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        if name.startswith("sqlite_"):
            continue
        cols = _table_columns(cur, name)
        if "tenant_id" in cols:
            leftover.append(name)
    findings.append(
        Finding(
            key="tenant_id_columns",
            details="Tables still containing tenant_id columns (should be empty)",
            count=len(leftover),
        )
    )

    # NULL company_id (only for tables that have the column)
    for table in [
        "alerts",
        "notifications",
        "api_tokens",
        "blocked_ips",
        "whitelisted_ips",
        "payment_methods",
        "subscriptions",
        "locations",
        "fcm_devices",
        "admin_broadcasts",
        "websocket_sessions",
        "user_settings",
        "csrf_tokens",
    ]:
        if not _has_table(cur, table):
            continue
        cols = _table_columns(cur, table)
        if "company_id" not in cols:
            continue
        add(
            key=f"{table}.company_id_null",
            details=f"{table}: rows where company_id IS NULL",
            sql=f"SELECT COUNT(*) FROM {table} WHERE company_id IS NULL",
        )

    # Notifications mismatched vs user
    if _has_table(cur, "notifications") and _has_table(cur, "users"):
        cols_n = _table_columns(cur, "notifications")
        cols_u = _table_columns(cur, "users")
        if {"company_id", "user_id"}.issubset(cols_n) and {"company_id", "id"}.issubset(cols_u):
            add(
                key="notifications.company_mismatch",
                details="notifications.company_id != users.company_id for same user",
                sql=(
                    "SELECT COUNT(*) "
                    "FROM notifications n "
                    "JOIN users u ON u.id = n.user_id "
                    "WHERE n.company_id IS NOT NULL AND u.company_id IS NOT NULL AND n.company_id != u.company_id"
                ),
            )

    con.close()
    return findings


def apply_fixes(db_path: Path) -> list[str]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    actions: list[str] = []

    def exec_and_record(sql: str, params: tuple = ()):
        cur.execute(sql, params)
        actions.append(f"{sql} | params={params} | rows={cur.rowcount}")

    # Backfill common tables company_id from users.company_id
    backfill_tables = [
        "alerts",
        "notifications",
        "api_tokens",
        "blocked_ips",
        "whitelisted_ips",
        "payment_methods",
        "subscriptions",
        "fcm_devices",
        "admin_broadcasts",
        "websocket_sessions",
        "user_settings",
    ]

    for table in backfill_tables:
        if not _has_table(cur, table):
            continue
        cols = _table_columns(cur, table)
        if not {"company_id", "user_id"}.issubset(cols):
            continue

        exec_and_record(
            f"UPDATE {table} "
            f"SET company_id = (SELECT company_id FROM users u WHERE u.id = {table}.user_id) "
            "WHERE company_id IS NULL AND user_id IS NOT NULL",
        )

    # Fix notifications with mismatched company_id (force to user.company_id)
    if _has_table(cur, "notifications"):
        cols = _table_columns(cur, "notifications")
        if {"company_id", "user_id"}.issubset(cols):
            exec_and_record(
                "UPDATE notifications "
                "SET company_id = (SELECT company_id FROM users u WHERE u.id = notifications.user_id) "
                "WHERE user_id IS NOT NULL AND company_id IS NOT NULL AND company_id != (SELECT company_id FROM users u WHERE u.id = notifications.user_id)",
            )

    # NOTE: csrf_tokens intentionally left alone (it does not have company_id in model).

    # Locations: this table has `company_id` but no `user_id` in schema, so we can't infer.
    # We keep this conservative by leaving it unchanged unless the caller has decided a policy.

    con.commit()
    con.close()
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan and optionally fix DB rows for company tenancy.")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to sqlite db (default: server/data/securecore.db)")
    parser.add_argument("--apply", action="store_true", help="Apply fixes (creates a backup first)")
    parser.add_argument(
        "--locations-policy",
        choices=["keep", "delete", "assign"],
        default="keep",
        help=(
            "What to do with location rows that have company_id IS NULL and cannot be inferred. "
            "keep=leave as-is (default), delete=remove them, assign=set to --default-company-id."
        ),
    )
    parser.add_argument(
        "--default-company-id",
        type=int,
        default=None,
        help="Company id to use with --locations-policy=assign",
    )
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    findings = scan(db_path)

    print(f"DB: {db_path}")
    print("\n== Scan report ==")
    for f in findings:
        # show only non-zero, except the tenant_id check
        if f.key == "tenant_id_columns" or f.count:
            print(f"- {f.key}: {f.count}  ({f.details})")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to fix.")
        return 0

    # Backup
    backup_path = BACKUP_DIR / f"securecore.db.bak.{_utc_stamp()}"
    shutil.copy2(db_path, backup_path)
    print(f"\nBackup created: {backup_path}")

    actions = apply_fixes(db_path)

    # Handle locations policy (post main backfills)
    if args.locations_policy != "keep":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        if _has_table(cur, "locations"):
            cols = _table_columns(cur, "locations")
            if "company_id" in cols:
                if args.locations_policy == "delete":
                    cur.execute("DELETE FROM locations WHERE company_id IS NULL")
                    actions.append(f"DELETE FROM locations WHERE company_id IS NULL | rows={cur.rowcount}")
                elif args.locations_policy == "assign":
                    if args.default_company_id is None:
                        raise SystemExit("--default-company-id is required when --locations-policy=assign")
                    # Ensure company exists
                    exists = cur.execute("SELECT 1 FROM companies WHERE id=?", (args.default_company_id,)).fetchone()
                    if not exists:
                        raise SystemExit(f"Company id not found: {args.default_company_id}")
                    cur.execute(
                        "UPDATE locations SET company_id=? WHERE company_id IS NULL",
                        (args.default_company_id,),
                    )
                    actions.append(
                        f"UPDATE locations SET company_id={args.default_company_id} WHERE company_id IS NULL | rows={cur.rowcount}"
                    )
        con.commit()
        con.close()
    print("\n== Applied fixes ==")
    for a in actions:
        print(f"- {a}")

    # Re-scan afterwards
    findings_after = scan(db_path)
    print("\n== Post-fix scan report ==")
    for f in findings_after:
        if f.key == "tenant_id_columns" or f.count:
            print(f"- {f.key}: {f.count}  ({f.details})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
