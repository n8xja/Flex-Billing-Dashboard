"""SQLite storage. One file (sophos.db) in the data folder."""
import sqlite3
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT, finished_at TEXT, status TEXT, message TEXT
);
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY, name TEXT, billing_type TEXT, api_host TEXT,
    data_region TEXT, updated_at TEXT
);
-- One row per tenant / product / day: live license counts (Flex usage)
CREATE TABLE IF NOT EXISTS license_snapshots (
    snap_date TEXT, tenant_id TEXT, product_code TEXT, product_name TEXT,
    license_type TEXT, count INTEGER,
    PRIMARY KEY (snap_date, tenant_id, product_code)
);
-- The monthly usage report, as published by Sophos (one row per report line)
CREATE TABLE IF NOT EXISTS billing_lines (
    month TEXT, line_no INTEGER, account_id TEXT, account_name TEXT,
    serial TEXT, product_code TEXT, product_description TEXT,
    product_group TEXT, sku TEXT, quantity REAL, unit_price REAL,
    PRIMARY KEY (month, line_no)
);
CREATE TABLE IF NOT EXISTS billing_months (
    month TEXT PRIMARY KEY, fetched_at TEXT, line_count INTEGER
);
-- Firewalls registered in Central, per day
CREATE TABLE IF NOT EXISTS fw_inventory (
    snap_date TEXT, serial TEXT, tenant_id TEXT, hostname TEXT, model TEXT,
    connected INTEGER, suspended INTEGER, cluster_status TEXT, cluster_peers TEXT,
    PRIMARY KEY (snap_date, serial)
);
-- Firewall licenses (all subscriptions on each serial), per day
CREATE TABLE IF NOT EXISTS fw_licenses (
    snap_date TEXT, serial TEXT, tenant_id TEXT, model TEXT, last_seen TEXT,
    licenses_json TEXT,
    PRIMARY KEY (snap_date, serial)
);
CREATE INDEX IF NOT EXISTS ix_ls_date ON license_snapshots(snap_date);
CREATE INDEX IF NOT EXISTS ix_bl_month ON billing_lines(month);
"""


def connect():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


@contextmanager
def session():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()
