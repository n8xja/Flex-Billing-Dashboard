"""Pulls data from Sophos into the local database.

Run once:            python -m app.collector --once
Run on a schedule:   python -m app.collector         (what the container does)
"""
import argparse
import datetime as dt
import json
import logging
import sys
import time

from . import config, db
from .sophos import Sophos, SophosError

log = logging.getLogger("collector")


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def months_back(n, today=None):
    today = today or dt.date.today()
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append((y, m))
    return out  # most recent first, excludes the current month


def collect(api=None, full_billing=False):
    api = api or Sophos()
    today = dt.date.today().isoformat()
    con = db.connect()
    run_id = con.execute("INSERT INTO runs(started_at,status) VALUES(?,?)", (now(), "running")).lastrowid
    con.commit()
    try:
        api.whoami()

        # 1. Tenants
        tenants = api.tenants()
        con.executemany(
            "INSERT OR REPLACE INTO tenants(id,name,billing_type,api_host,data_region,updated_at) VALUES(?,?,?,?,?,?)",
            [(t["id"], " ".join((t.get("showAs") or t.get("name") or "").split()), t.get("billingType"),
              t.get("apiHost"), t.get("dataRegion"), now()) for t in tenants])
        con.commit()
        log.info("tenants: %d", len(tenants))

        # 2. Live license counts per tenant
        con.execute("DELETE FROM license_snapshots WHERE snap_date=?", (today,))
        n = 0
        skipped = []
        for t in tenants:
            try:
                tlic = api.tenant_licenses(t["id"])
            except SophosError as e:
                skipped.append(t["id"]); log.warning("licenses skipped for %s: %s", t.get("name"), e); continue
            for lic in tlic:
                cur = (lic.get("usage") or {}).get("current") or {}
                p = lic.get("product") or {}
                con.execute(
                    "INSERT INTO license_snapshots VALUES(?,?,?,?,?,?) "
                    "ON CONFLICT(snap_date,tenant_id,product_code) DO UPDATE SET count=count+excluded.count",
                    (today, t["id"], p.get("code"), p.get("name"), lic.get("type"), cur.get("count") or 0))
                n += 1
            time.sleep(0.2)
        con.commit()
        log.info("license rows: %d", n)

        # 3. Firewalls registered in Central
        con.execute("DELETE FROM fw_inventory WHERE snap_date=?", (today,))
        for t in tenants:
            if not t.get("apiHost"):
                continue
            try:
                fws = api.tenant_firewalls(t["id"], t["apiHost"])
            except SophosError as e:
                skipped.append(t["id"]); log.warning("firewalls skipped for %s: %s", t.get("name"), e); continue
            for f in fws:
                cl = f.get("cluster") or {}
                st = f.get("status") or {}
                con.execute("INSERT OR REPLACE INTO fw_inventory VALUES(?,?,?,?,?,?,?,?,?)", (
                    today, (f.get("serialNumber") or "").upper(), t["id"], f.get("hostname"), f.get("model"),
                    1 if st.get("connected") else 0, 1 if st.get("suspended") else 0, cl.get("status"),
                    json.dumps([(p.get("serialNumber") or "").upper() for p in cl.get("peers", [])])))
            time.sleep(0.2)
        con.commit()

        # 4. Firewall licenses (partner-wide)
        con.execute("DELETE FROM fw_licenses WHERE snap_date=?", (today,))
        for item in api.firewall_licenses():
            con.execute("INSERT OR REPLACE INTO fw_licenses VALUES(?,?,?,?,?,?)", (
                today, (item.get("serialNumber") or "").upper(), (item.get("tenant") or {}).get("id"),
                item.get("model"), item.get("lastSeenAt"), json.dumps(item.get("licenses", []))))
        con.commit()

        # 5. Monthly usage reports: fetch any missing month, and always re-fetch the latest two
        have = {r["month"] for r in con.execute("SELECT month FROM billing_months")}
        for i, (y, m) in enumerate(months_back(config.RETENTION_MONTHS)):
            key = f"{y}-{m:02d}"
            if key in have and i >= 2 and not full_billing:
                continue
            lines = api.billing_usage(y, m)
            if lines is None:
                continue
            con.execute("DELETE FROM billing_lines WHERE month=?", (key,))
            con.executemany("INSERT INTO billing_lines VALUES(?,?,?,?,?,?,?,?,?,?,?)", [(
                key, idx, l.get("accountId"), (l.get("assignedAccountIdentifier") or "").strip(),
                (l.get("accountNumberOrSerialNumber") or "").upper(), l.get("productCode"),
                l.get("productDescription"), l.get("productGroup"), l.get("sku"),
                float(l.get("billableQuantity") or 0), float(l.get("unitPrice") or 0)) for idx, l in enumerate(lines)])
            con.execute("INSERT OR REPLACE INTO billing_months VALUES(?,?,?)", (key, now(), len(lines)))
            con.commit()
            log.info("billing %s: %d lines", key, len(lines))

        # 6. Retention
        cutoff = (dt.date.today() - dt.timedelta(days=int(config.RETENTION_MONTHS * 30.5))).isoformat()
        cutoff_month = cutoff[:7]
        for table in ("license_snapshots", "fw_inventory", "fw_licenses"):
            con.execute(f"DELETE FROM {table} WHERE snap_date < ?", (cutoff,))
        con.execute("DELETE FROM billing_lines WHERE month < ?", (cutoff_month,))
        con.execute("DELETE FROM billing_months WHERE month < ?", (cutoff_month,))
        con.execute("DELETE FROM runs WHERE started_at < ?", (cutoff,))

        con.execute("UPDATE runs SET finished_at=?, status=?, message=? WHERE id=?",
                    (now(), "ok", f"{len(tenants)} tenants" + (f", {len(skipped)} tenant calls skipped (see log)" if skipped else ""), run_id))
        con.commit()
        log.info("collection finished")
    except Exception as e:  # record the failure so the dashboard can show it
        log.exception("collection failed")
        con.execute("UPDATE runs SET finished_at=?, status=?, message=? WHERE id=?",
                    (now(), "failed", str(e)[:500], run_id))
        con.commit()
        raise
    finally:
        con.close()


def collected_today():
    with db.session() as con:
        r = con.execute("SELECT 1 FROM runs WHERE status='ok' AND started_at >= ? LIMIT 1",
                        (dt.date.today().isoformat(),)).fetchone()
        return r is not None


def ever_collected():
    with db.session() as con:
        return con.execute("SELECT 1 FROM runs WHERE status='ok' LIMIT 1").fetchone() is not None


def loop():
    log.info("collector started; daily run at %02d:00, checking for manual refresh every minute", config.COLLECT_HOUR)
    while True:
        due = (not ever_collected()) or (dt.datetime.now().hour >= config.COLLECT_HOUR and not collected_today())
        manual = config.REFRESH_FLAG.exists()
        if due or manual:
            if manual:
                config.REFRESH_FLAG.unlink(missing_ok=True)
                log.info("manual refresh requested from the dashboard")
            try:
                collect()
            except Exception:
                time.sleep(15 * 60)  # wait before retrying after a failure
        time.sleep(60)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="collect once and exit")
    ap.add_argument("--full-billing", action="store_true", help="re-download every monthly report")
    a = ap.parse_args()
    if a.once:
        collect(full_billing=a.full_billing)
    else:
        loop()


if __name__ == "__main__":
    main()
