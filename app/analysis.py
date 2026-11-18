"""Turns the stored data into the tables the dashboard shows."""
import datetime as dt
import json
import re
import statistics
from collections import defaultdict

import pandas as pd

from . import config

TYPE = config.TYPE_LABELS


# ---------------------------------------------------------------- helpers --
def tenants(con):
    return {r["id"]: dict(r) for r in con.execute("SELECT * FROM tenants")}


def latest_snapshot(con):
    r = con.execute("SELECT MAX(snap_date) d FROM license_snapshots").fetchone()
    return r["d"]


def latest_fw_snapshot(con):
    r = con.execute("SELECT MAX(snap_date) d FROM fw_licenses").fetchone()
    return r["d"]


def billing_months(con):
    return [r["month"] for r in con.execute("SELECT month FROM billing_months ORDER BY month")]


def customer_name(tn, account_id, fallback):
    t = tn.get(account_id)
    return t["name"] if t else " ".join((fallback or "(unknown)").split())


def customer_type(tn, account_id):
    t = tn.get(account_id)
    return TYPE.get(t["billing_type"], t["billing_type"] or "?") if t else "Not a current tenant"


def fw_base(code):
    return re.sub(r"-USAUSD-.*$", "", code or "").upper()


def short_product(d):
    d = re.sub(r" - (MSP|USAUSD).*$", "", d or "")
    for a, b in [("Sophos ", ""), ("SF SW/Virtual ", "Virtual FW "), (" - UP TO ", " "), (" & UNL RAM", ""),
                 ("Standard Protection", "Std"), ("Xstream Protection", "Xstream"),
                 ("Appliance as Service", "appliance"), (" for Email MSP Monthly", "")]:
        d = d.replace(a, b)
    return d.strip()


def product_line(desc, group):
    if group == "Device":
        return "Firewalls" if re.search(r"XGS|SF SW|SG |XG ", desc or "") else "Switches & APs"
    if "Email" in desc or "DMARC" in desc:
        return "Email"
    if "MDR" in desc:
        return "MDR"
    if "XDR" in desc or "EDR" in desc:
        return "XDR / EDR"
    return "Endpoint & other"


def firewall_serials(con, snap):
    s = {r["serial"] for r in con.execute("SELECT serial FROM fw_licenses WHERE snap_date=?", (snap,))}
    s |= {r["serial"] for r in con.execute("SELECT serial FROM fw_inventory WHERE snap_date=?", (snap,))}
    return s


# ------------------------------------------------------------ Flex changes --
def flex_changes(con):
    """Last usage report vs. what is live today. Returns (DataFrame, info dict)."""
    months = billing_months(con)
    snap = latest_snapshot(con)
    fsnap = latest_fw_snapshot(con)
    if not months or not snap:
        return pd.DataFrame(), {}
    month = months[-1]
    tn = tenants(con)
    flex_ids = {i for i, t in tn.items() if t["billing_type"] == "usage"}
    fw_serials = firewall_serials(con, fsnap) if fsnap else set()
    lic_codes = {r["product_code"] for r in con.execute(
        "SELECT DISTINCT product_code FROM license_snapshots WHERE snap_date=?", (snap,))}

    lines = [dict(r) for r in con.execute("SELECT * FROM billing_lines WHERE month=?", (month,))]
    rows = []

    # --- users / servers / other per-tenant products (Flex tenants)
    billed, price, prices_by_code = defaultdict(float), {}, defaultdict(list)
    for l in lines:
        if l["serial"] in fw_serials or l["product_code"] not in lic_codes or l["account_id"] not in flex_ids:
            continue
        k = (l["account_id"], l["product_code"])
        billed[k] += l["quantity"]
        price[k] = l["unit_price"]
        prices_by_code[l["product_code"]].append(l["unit_price"])
    live, pname = {}, {}
    for r in con.execute("SELECT * FROM license_snapshots WHERE snap_date=? AND license_type='usage'", (snap,)):
        if r["tenant_id"] in flex_ids:
            live[(r["tenant_id"], r["product_code"])] = r["count"] or 0
            pname[r["product_code"]] = r["product_name"]
    for k in set(billed) | {k for k, v in live.items() if v > 0}:
        bq, lq = billed.get(k, 0), live.get(k, 0)
        if bq == lq:
            continue
        tid, code = k
        p = price.get(k) or (statistics.median(prices_by_code[code]) if prices_by_code[code] else None)
        rows.append(dict(Customer=customer_name(tn, tid, None), Type=customer_type(tn, tid), Category="Users & servers",
                         Product=" ".join((pname.get(code) or code).split()), Billed=bq, Live=lq,
                         UnitPrice=p, Basis="Customer's price on report" if k in price else
                         ("Estimate (typical price)" if p else "No price found"), Note=""))

    # --- firewalls (matched by serial, whatever the tenant's billing type)
    if fsnap:
        snap_day = dt.date.fromisoformat(fsnap)
        fb, fprice, fpc, fcust = defaultdict(float), {}, defaultdict(list), {}
        for l in lines:
            if l["serial"] not in fw_serials:
                continue
            k = (l["serial"], fw_base(l["product_code"]))
            fb[k] += l["quantity"]
            fprice[k] = l["unit_price"]
            fpc[k[1]].append(l["unit_price"])
            fcust[l["serial"]] = (l["account_id"], l["account_name"])
            pname[k[1]] = short_product(l["product_description"])
        flive, fstale = {}, {}
        inv = {r["serial"]: dict(r) for r in con.execute("SELECT * FROM fw_inventory WHERE snap_date=?", (fsnap,))}
        fwl = {r["serial"]: dict(r) for r in con.execute("SELECT * FROM fw_licenses WHERE snap_date=?", (fsnap,))}
        for s, L in fwl.items():
            recent, last = False, None
            if L["last_seen"]:
                last = dt.datetime.fromisoformat(L["last_seen"].replace("Z", "+00:00")).date()
                recent = (snap_day - last).days <= config.FIREWALL_STALE_DAYS
            for lic in json.loads(L["licenses_json"]):
                if lic.get("type") != "usage":
                    continue
                k = (s, fw_base(lic["product"]["code"]))
                c = ((lic.get("usage") or {}).get("current") or {}).get("count") or 0
                flive[k] = c if recent else 0
                fstale[k] = last
                pname.setdefault(k[1], lic["product"].get("name") or k[1])
        for k in set(fb) | {k for k, v in flive.items() if v > 0}:
            bq, lq = fb.get(k, 0), flive.get(k, 0)
            if bq == lq:
                continue
            s, code = k
            tid = (inv.get(s) or {}).get("tenant_id") or (fwl.get(s) or {}).get("tenant_id")
            acct, aname = fcust.get(s, (None, None))
            p = fprice.get(k) or (statistics.median(fpc[code]) if fpc[code] else None)
            host = (inv.get(s) or {}).get("hostname") or ""
            note = ""
            if lq == 0 and fstale.get(k):
                note = f"Stopped reporting {fstale[k]:%b %d}; may drop off the next bill"
            rows.append(dict(Customer=customer_name(tn, tid or acct, aname), Type=customer_type(tn, tid or acct),
                             Category="Firewall", Product=f"{pname.get(code, code)} | {s}" + (f" ({host})" if host else ""),
                             Billed=bq, Live=lq, UnitPrice=p,
                             Basis="Customer's price on report" if k in fprice else
                             ("Estimate (typical price)" if p else "No price found"), Note=note))

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Change"] = df["Live"] - df["Billed"]
        df["Monthly impact"] = df["Change"] * df["UnitPrice"].fillna(0)
        df = df.sort_values("Monthly impact", key=lambda s: -s.abs()).reset_index(drop=True)
    return df, {"month": month, "snapshot": snap, "fw_snapshot": fsnap}


# ------------------------------------------------------- Firewall checks --
def firewall_exceptions(con):
    snap = latest_fw_snapshot(con)
    months = billing_months(con)
    if not snap:
        return pd.DataFrame(), {}
    today = snap
    tn = tenants(con)
    inv = {r["serial"]: dict(r) for r in con.execute("SELECT * FROM fw_inventory WHERE snap_date=?", (snap,))}
    fwl = {r["serial"]: dict(r) for r in con.execute("SELECT * FROM fw_licenses WHERE snap_date=?", (snap,))}
    billed = defaultdict(list)
    if months:
        for l in con.execute("SELECT * FROM billing_lines WHERE month=?", (months[-1],)):
            if l["serial"] in inv or l["serial"] in fwl:
                billed[l["serial"]].append(dict(l))

    def lic_state(s):
        ls = json.loads((fwl.get(s) or {}).get("licenses_json") or "[]")
        usage = [l for l in ls if l.get("type") == "usage"]
        term = [l for l in ls if l.get("type") == "term" and (l.get("endDate") or "") >= today]
        trial = [l for l in ls if l.get("type") == "trial" and (l.get("endDate") or "") >= today]
        expired = [l for l in ls if l.get("type") == "term" and (l.get("endDate") or "") < today]
        return usage, term, trial, expired

    snap_day = dt.date.fromisoformat(snap)
    rows = []
    for s in set(inv) | set(fwl) | set(billed):
        f, L, B = inv.get(s), fwl.get(s) or {}, billed.get(s, [])
        usage, term, trial, expired = lic_state(s)
        covered = bool(usage or term or trial)
        role = {"primary": "HA primary", "auxiliary": "HA standby"}.get((f or {}).get("cluster_status"), "Standalone") if f else "—"
        peers = json.loads((f or {}).get("cluster_peers") or "[]")
        peer_cov = any(any(lic_state(p)[:3]) for p in peers)
        tid = (f or {}).get("tenant_id") or L.get("tenant_id")
        acct = B[0]["account_id"] if B else None
        cust = customer_name(tn, tid or acct, B[0]["account_name"] if B else "(unassigned)")
        ctype = customer_type(tn, tid) if tid in tn else ("Billed, not in Central" if B else "Unassigned")
        cost = sum(b["quantity"] * b["unit_price"] for b in B)
        last = None
        if L.get("last_seen"):
            last = dt.datetime.fromisoformat(L["last_seen"].replace("Z", "+00:00")).date()
        stale = last is None or (snap_day - last).days > config.FIREWALL_STALE_DAYS
        connected = None if not f else bool(f["connected"])
        issue = action = None
        prio = 9
        if usage and term:
            prio, issue = 1, "Paying twice"
            action = f"Flex subscription active while a term license runs to {max(t['endDate'] for t in term)}. Drop the Flex subscription."
        elif B and connected is False:
            prio, issue = 2, "Billed while offline"
            action = "Billed but not connected to Central." + (" This is the HA standby unit carrying the pair's subscription." if role == "HA standby" else " Bring it back online or cancel.")
        elif f and connected and not covered and not (role == "HA standby" and peer_cov):
            prio = 3 if ctype == config.LABEL_FLEX else 4
            issue = "No protection"
            if expired:
                action = f"Term subscription expired {max(e['endDate'] for e in expired)}. Renew, move to Flex, or retire."
            elif role == "HA primary":
                action = "HA primary with no subscription. Check which unit of the pair carries the license."
            else:
                action = "Connected but has no security subscription. Add Flex protection (it will then bill) and charge the customer."
            if prio == 4:
                action = f"Monitor only (not a {config.LABEL_FLEX} customer). " + action
        elif usage and not B and stale:
            prio, issue = 5, "Stale Flex subscription"
            action = f"Flex subscription on a unit last seen {last or 'never'}. Not billing now but will if it comes back online. Clean up if retired."
        elif usage and not B:
            prio, issue = 3, "New Flex subscription"
            action = "Has a Flex subscription but was not on the last report. It should appear on the next bill; charge the customer."
        elif B and not f:
            prio, issue = 6, "Billed, not managed in Central"
            action = "Licensed and reporting, but not registered for Central management."
        if issue:
            rows.append({"Priority": prio, "Issue": issue, "Customer": cust, "Customer type": ctype,
                         "Hostname": (f or {}).get("hostname") or "", "Model": ((L.get("model") or (f or {}).get("model") or "").split("_")[0]),
                         "Serial": s, "HA role": role, "Connected": {True: "Yes", False: "No", None: "—"}[connected],
                         "Last seen": str(last or ""), "Billed ($/mo)": round(cost, 2), "What to do": action})
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["Priority", "Customer", "Hostname"]).reset_index(drop=True)
    total = 0.0
    if months:
        total = sum(sum(b["quantity"] * b["unit_price"] for b in v) for v in billed.values())
    return df, {"snapshot": snap, "month": months[-1] if months else None, "firewall_billing": total}


# ------------------------------------------------------------------ Trends --
def trends(con, n_months):
    months = billing_months(con)[-n_months:]
    if not months:
        return None
    tn = tenants(con)
    q = "SELECT * FROM billing_lines WHERE month IN (%s)" % ",".join("?" * len(months))
    lines = [dict(r) for r in con.execute(q, months)]
    df = pd.DataFrame(lines)
    df["Cost"] = df["quantity"] * df["unit_price"]
    df["Customer"] = [customer_name(tn, a, n) for a, n in zip(df["account_id"], df["account_name"])]
    df["Type"] = [customer_type(tn, a) for a in df["account_id"]]
    df["Product line"] = [product_line(d, g) for d, g in zip(df["product_description"], df["product_group"])]
    df["Product"] = df["product_description"].map(short_product)

    by_line = df.pivot_table(index="Product line", columns="month", values="Cost", aggfunc="sum", fill_value=0)
    by_line.loc["Total"] = by_line.sum()

    first, last = months[0], months[-1]
    cust = df.pivot_table(index=["Customer", "Type"], columns="month", values="Cost", aggfunc="sum", fill_value=0)
    prod = df.pivot_table(index=["Customer", "Product"], columns="month", values="Cost", aggfunc="sum", fill_value=0)
    notes = {}
    for (c, t), row in cust.iterrows():
        P = {p: (v[first], v[last]) for (cc, p), v in prod.loc[[c]].iterrows() if abs(v[last] - v[first]) >= 0.005} if c in prod.index.get_level_values(0) else {}
        parts = []
        for old, new in config.PRODUCT_MOVES:
            if old in P and new in P and P[old][1] == 0 and P[new][0] == 0 and row[first] > 0:
                d = P[new][1] - P[old][0]
                parts.append(f"Moved {old} → {new}" + (f" ({'+' if d > 0 else '−'}${abs(d):,.2f})" if abs(d) >= 0.005 else " (same cost)"))
                P.pop(old), P.pop(new)
        for p, (a, b) in sorted(P.items(), key=lambda x: -abs(x[1][1] - x[1][0]))[:3]:
            tag = " (new)" if a == 0 else (" (ended)" if b == 0 else "")
            d = b - a
            parts.append(f"{p}{tag} {'+' if d > 0 else '−'}${abs(d):,.2f}")
        if row[first] == 0:
            notes[(c, t)] = "New customer in this period: " + "; ".join(parts)
        elif row[last] == 0:
            notes[(c, t)] = "No longer billed"
        else:
            notes[(c, t)] = "; ".join(parts) or "No change"
    cust = cust.reset_index()
    cust["Change"] = cust[last] - cust[first]
    cust["Change %"] = [None if a == 0 else (b - a) / a for a, b in zip(cust[first], cust[last])]
    cust["What changed"] = [notes[(c, t)] for c, t in zip(cust["Customer"], cust["Type"])]
    cust = cust.sort_values("Change", key=lambda s: -s.abs()).reset_index(drop=True)

    groups = {}
    for prefix in config.GROUP_PREFIXES:
        g = df[df["Customer"].str.lower().str.startswith(prefix.lower())]
        if g.empty:
            continue
        mdr = g[g["product_description"].str.contains("MDR")]
        tbl = pd.DataFrame({
            "Tenants billed": g.groupby("month")["Customer"].nunique(),
            "MDR users": mdr[mdr["product_group"] == "User"].groupby("month")["quantity"].sum(),
            "MDR servers": mdr[mdr["product_group"] == "Server"].groupby("month")["quantity"].sum(),
            "MDR cost": mdr.groupby("month")["Cost"].sum(),
            "Total cost": g.groupby("month")["Cost"].sum(),
        }).reindex(months).fillna(0).T
        groups[prefix] = tbl
    return {"months": months, "by_line": by_line, "customers": cust, "groups": groups}


# ------------------------------------------------- Group license counts --
def _license_name(desc, group):
    """Short licence name plus its unit, e.g. 'MDR Plus users'."""
    p = re.sub(r"\s*-\s*(User|Users|Server|Servers)$", "", short_product(desc))
    return p, {"User": " users", "Server": " servers"}.get(group, "")


def group_license_counts(con, months, prefix):
    """License quantities (no costs) per tenant whose name starts with `prefix`.

    One row per tenant and licence, one column per month. Product moves from
    PRODUCT_MOVES are followed, so a tenant that moved from MDR Complete to
    MDR Plus stays on one row, with a note saying when it moved.
    """
    if not months:
        return pd.DataFrame()
    tn = tenants(con)
    moves = dict(config.PRODUCT_MOVES)

    def canonical(p):
        seen = set()
        while p in moves and p not in seen:  # follow Old>New chains
            seen.add(p)
            p = moves[p]
        return p

    q = "SELECT * FROM billing_lines WHERE month IN (%s)" % ",".join("?" * len(months))
    qty = defaultdict(lambda: [0.0] * len(months))
    names = defaultdict(lambda: [set() for _ in months])
    for l in con.execute(q, months):
        cust = customer_name(tn, l["account_id"], l["account_name"])
        if not cust.lower().startswith(prefix.lower()):
            continue
        prod, unit = _license_name(l["product_description"], l["product_group"])
        key = (cust, canonical(prod) + unit)
        i = months.index(l["month"])
        qty[key][i] += l["quantity"]
        names[key][i].add(prod)

    label = lambda m: dt.date.fromisoformat(m + "-01").strftime("%b %Y")
    full = lambda m: dt.date.fromisoformat(m + "-01").strftime("%B")
    rows = []
    for (cust, lic), v in qty.items():
        seen = [i for i, x in enumerate(v) if x]
        notes = []
        if seen and seen[0] > 0:
            notes.append(f"New in {full(months[seen[0]])}")
        if seen and seen[-1] < len(months) - 1:
            notes.append(f"Not billed after {full(months[seen[-1]])}")
        prods = [names[(cust, lic)][i] for i in seen]
        for a, b, i in zip(prods, prods[1:], seen[1:]):
            if a and b and a != b:
                notes.append(f"Moved from {', '.join(sorted(a))} to {', '.join(sorted(b))} in {full(months[i])}")
        row = {"Tenant": cust, "License": lic}
        row.update({label(m): int(round(x)) for m, x in zip(months, v)})
        row[f"Change {label(months[0])} to {label(months[-1])}"] = int(round(v[-1] - v[0]))
        row["Notes"] = "; ".join(n if i == 0 else n[0].lower() + n[1:] for i, n in enumerate(notes))
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(["Tenant", "License"], key=lambda s: s.str.lower()).reset_index(drop=True)
    num = [c for c in df.columns if c not in ("Tenant", "License", "Notes")]
    totals = df.groupby("License")[num].sum().reset_index()
    totals.insert(0, "Tenant", f"Total, all {prefix} tenants")
    totals["Notes"] = ""
    return pd.concat([df, totals], ignore_index=True)
