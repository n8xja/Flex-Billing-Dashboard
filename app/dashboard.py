"""Web dashboard (Streamlit). Started by the container; open it in a browser."""
import datetime as dt
import time

import pandas as pd
import streamlit as st

# Streamlit puts only this file's folder (app/) on the import path. Add the
# project folder above it so "from app import ..." works however it's started.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import analysis, config, db, users  # noqa: E402

_icon = config.branding_file(config.BRAND_ICON)
st.set_page_config(page_title=config.BRAND_NAME, page_icon=str(_icon) if _icon else (config.BRAND_ICON or None), layout="wide")
_logo = config.branding_file(config.BRAND_LOGO)
if _logo:
    st.logo(str(_logo))
DAY = config.ordinal(config.BILLING_DAY)
FLEX = config.LABEL_FLEX


def footer():
    if config.BRAND_FOOTER:
        st.divider()
        st.caption(config.BRAND_FOOTER)

# Translucent fills with mid-tone text read well on both light and dark themes.
GREEN = "background-color:rgba(34,160,90,0.18);color:#2f9e5f;font-weight:600"
RED = "background-color:rgba(220,70,70,0.18);color:#d64545;font-weight:600"


def client_ip():
    """The viewer's address as seen by the HTTPS proxy (last X-Forwarded-For entry)."""
    try:
        xff = st.context.headers.get("X-Forwarded-For", "")
        return xff.split(",")[-1].strip() or "unknown"
    except Exception:
        return "unknown"


def safe_csv(df):
    """CSV text that spreadsheet programs won't run as formulas (CSV injection).

    Any text cell starting with = + - @ or a tab/return gets a leading apostrophe.
    """
    def fix(v):
        return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = out[c].map(fix)
    return out.to_csv(index=False)


# ----------------------------------------------------------------- sign-in --
def sign_in():
    now = time.time()
    if st.session_state.get("user"):
        idle = now - st.session_state.get("last_seen", now)
        if idle <= config.SESSION_TIMEOUT_MINUTES * 60:
            st.session_state.last_seen = now
            return True
        users.log.info("session timed out: user=%r", st.session_state.user)
        st.session_state.clear()
        st.session_state.timed_out = True
    st.title(config.BRAND_NAME)
    if config.BRAND_TAGLINE:
        st.write(config.BRAND_TAGLINE)
    if st.session_state.pop("timed_out", False):
        st.info("You were signed out after a period of inactivity. Please sign in again.")
    with st.form("login"):
        u = st.text_input("User name")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
    if ok:
        time.sleep(1)  # slows down password guessing
        good, message = users.attempt(u, p, client_ip())
        if good:
            st.session_state.clear()          # fresh session after sign-in
            st.session_state.user = u.strip().lower()
            st.session_state.last_seen = time.time()
            st.rerun()
        else:
            st.error(message)
    if not users.load():
        st.info("No users have been set up yet. Follow the 'Create your sign-in' step in the install guide.")
    footer()
    return False


if not sign_in():
    st.stop()


# ------------------------------------------------------------------ helpers --
def money(v):
    return "" if pd.isna(v) else (f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}")


def color_change(v):
    try:
        return GREEN if v > 0.005 else (RED if v < -0.005 else "")
    except TypeError:
        return ""


def month_label(m):
    return dt.date.fromisoformat(m + "-01").strftime(f"%b {config.BILLING_DAY}, %Y")


con = db.connect()
last_run = con.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
last_ok = con.execute("SELECT * FROM runs WHERE status='ok' ORDER BY id DESC LIMIT 1").fetchone()

with st.sidebar:
    if config.BRAND_ORG:
        st.markdown(f"### {config.BRAND_ORG}")
    st.markdown(f"Signed in as **{st.session_state.user}**")
    page = st.radio("Page", [f"{FLEX} changes", "Firewalls", "Trends", "Data status"], label_visibility="collapsed")
    st.divider()
    if last_ok:
        st.caption(f"Data last collected {last_ok['finished_at'].replace('T', ' ')}")
    if last_run and last_run["status"] == "running":
        st.info("A data collection is running now. Refresh the page in a few minutes.")
    elif config.REFRESH_FLAG.exists():
        st.info("Refresh requested. It starts within a minute and takes about 10 minutes.")
    elif st.button("Collect fresh data now"):
        config.REFRESH_FLAG.touch()
        st.rerun()
    st.caption("Light or dark: open the menu **⋮** at the top right of the page and pick a theme. "
               "This browser remembers your choice.")
    if st.button("Sign out"):
        users.log.info("signed out: user=%r", st.session_state.user)
        st.session_state.clear()
        st.rerun()

if not last_ok:
    st.title(config.BRAND_NAME)
    if last_run and last_run["status"] == "failed":
        st.error(f"The first data collection failed: {last_run['message']}")
        st.write("Check the Sophos API ID and secret in the .env file, then restart (see the install guide).")
    else:
        st.info("The first data collection is running. It takes about 10 to 15 minutes. Refresh this page after that.")
    st.stop()


# ------------------------------------------------------------- Flex changes --
if page == f"{FLEX} changes":
    df, info = analysis.flex_changes(con)
    st.title(f"{FLEX} changes since the last bill")
    if df.empty:
        st.success(f"Every {FLEX} quantity matches the last usage report.")
        st.stop()
    st.caption(f"Compares the usage report Sophos published for **{month_label(info['month'])}** with live counts "
               f"collected **{info['snapshot']}**. Use this before the {DAY} to adjust what you charge each customer.")
    f1, f2, f3 = st.columns(3)
    types = f1.multiselect("Customer type", sorted(df["Type"].unique()), default=[t for t in [FLEX] if t in set(df["Type"])] or None)
    cats = f2.multiselect("Category", sorted(df["Category"].unique()))
    search = f3.text_input("Customer name contains")
    v = df.copy()
    if types:
        v = v[v["Type"].isin(types)]
    if cats:
        v = v[v["Category"].isin(cats)]
    if search:
        v = v[v["Customer"].str.contains(search, case=False)]
    up = v[v["Change"] > 0]
    down = v[v["Change"] < 0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Increases (bill customers more)", money(up["Monthly impact"].sum()), f"{len(up)} lines")
    c2.metric("Decreases (bill customers less)", money(down["Monthly impact"].sum()), f"{len(down)} lines", delta_color="off")
    c3.metric("Net monthly change", money(v["Monthly impact"].sum()))
    show = v[["Customer", "Type", "Category", "Product", "Billed", "Live", "Change", "UnitPrice", "Monthly impact", "Basis", "Note"]]
    st.dataframe(
        show.style.map(color_change, subset=["Change", "Monthly impact"])
            .format({"UnitPrice": money, "Monthly impact": money, "Billed": "{:,.0f}", "Live": "{:,.0f}", "Change": "{:+,.0f}"}),
        hide_index=True, width="stretch", height=600,
        column_config={"UnitPrice": "Unit price", "Billed": f"Billed ({info['month']})", "Live": f"Live ({info['snapshot']})"})
    st.download_button("Download as CSV", safe_csv(show), f"flex-changes-{info['snapshot']}.csv", "text/csv")

# ---------------------------------------------------------------- Firewalls --
elif page == "Firewalls":
    df, info = analysis.firewall_exceptions(con)
    st.title("Firewall licensing checks")
    st.caption(f"Firewall serials on the {month_label(info['month']) if info.get('month') else 'latest'} usage report, "
               f"matched to Central and to each unit's licenses as of **{info.get('snapshot')}**. "
               "HA standby units are treated as covered when their primary is licensed.")
    if df.empty:
        st.success("No firewall licensing issues found.")
        st.stop()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Firewall billing on last report", money(info["firewall_billing"]))
    c2.metric("Paying twice", money(df.loc[df["Issue"] == "Paying twice", "Billed ($/mo)"].sum()))
    c3.metric("Billed while offline", money(df.loc[df["Issue"] == "Billed while offline", "Billed ($/mo)"].sum()))
    c4.metric(f"{FLEX} firewalls with no protection", int(((df["Issue"] == "No protection") & (df["Customer type"] == FLEX)).sum()))
    issues = st.multiselect("Issue", list(dict.fromkeys(df["Issue"])), default=None)
    v = df[df["Issue"].isin(issues)] if issues else df
    st.dataframe(v.style.format({"Billed ($/mo)": money}), hide_index=True, width="stretch", height=600)
    st.download_button("Download as CSV", safe_csv(v), f"firewalls-{info['snapshot']}.csv", "text/csv")

# ------------------------------------------------------------------- Trends --
elif page == "Trends":
    st.title("Billing trend")
    available = len(analysis.billing_months(con))
    options = [n for n in (3, 6, 12, 24) if n <= max(available, 3)]
    n = st.segmented_control("Period", options, default=options[0], format_func=lambda x: f"{x} months") or options[0]
    t = analysis.trends(con, n + 1)
    if not t:
        st.info("No usage reports collected yet.")
        st.stop()
    months = t["months"]
    first, last = months[0], months[-1]
    st.caption(f"From the usage report on each {DAY}: {month_label(first)} to {month_label(last)}. "
               "Green is growth, red is loss.")

    bl = t["by_line"].copy()
    bl["Change"] = bl[last] - bl[first]
    bl["Change %"] = [None if a == 0 else (b - a) / a for a, b in zip(bl[first], bl[last])]
    total = bl.loc["Total"]
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Monthly bill, {month_label(first)}", money(total[first]))
    c2.metric(f"Monthly bill, {month_label(last)}", money(total[last]), money(total["Change"]))
    c3.metric("Change", f"{total['Change %']:+.1%}" if total["Change %"] is not None else "")

    st.subheader("By product line")
    st.bar_chart(t["by_line"].drop(index="Total").T.rename(index=month_label), stack=True)
    st.dataframe(bl.style.map(color_change, subset=["Change"])
                 .format({**{m: money for m in months}, "Change": money, "Change %": lambda x: "" if x is None or pd.isna(x) else f"{x:+.1%}"}),
                 width="stretch")

    for prefix, g in t["groups"].items():
        st.subheader(f"{prefix} call-out (all {prefix} tenants combined)")
        g = g.copy()
        g["Change"] = g[last] - g[first]
        st.dataframe(g.style.format(lambda x: f"{x:,.2f}" if isinstance(x, float) and x % 1 else f"{x:,.0f}")
                     .map(color_change, subset=["Change"]), width="stretch")
        st.caption(f"Individual {prefix} tenants are still listed in the customer table below.")

        safe = "".join(ch if ch.isalnum() else "-" for ch in prefix).strip("-").lower() or "group"
        tab_cost, tab_counts = st.tabs([f"{prefix} tenants (with costs)", f"{prefix} license counts (no costs)"])

        with tab_cost:
            gc = t["customers"][t["customers"]["Customer"].str.lower().str.startswith(prefix.lower())]
            gc = gc.sort_values("Change", key=lambda s: -s.abs())
            st.caption("For your own use. Costs are Sophos's price to you.")
            st.dataframe(gc.style.map(color_change, subset=["Change"])
                         .format({**{m: money for m in months}, "Change": money,
                                  "Change %": lambda x: "new" if x is None or pd.isna(x) else f"{x:+.1%}"}),
                         hide_index=True, width="stretch", height=420,
                         column_config={m: month_label(m) for m in months})
            st.download_button(f"Download {prefix} tenants as CSV (with costs)", safe_csv(gc),
                               f"{safe}-tenants-{first}-to-{last}.csv", "text/csv", key=f"dl-cost-{safe}")

        with tab_counts:
            lc = analysis.group_license_counts(con, months, prefix)
            if lc.empty:
                st.info(f"No licenses found for {prefix} in this period.")
            else:
                change_col = [c for c in lc.columns if c.startswith("Change")][0]
                st.caption("License quantities only: no prices or costs, so this table is safe to send to the customer.")
                st.dataframe(lc.style.map(lambda v: color_change(v), subset=[change_col])
                             .format({change_col: "{:+d}"}),
                             hide_index=True, width="stretch", height=420)
                st.download_button(f"Download {prefix} license counts as CSV (no costs)", safe_csv(lc),
                                   f"{safe}-license-counts-{first}-to-{last}.csv", "text/csv", key=f"dl-counts-{safe}")

    st.subheader("By customer (largest change first)")
    cust = t["customers"]
    f1, f2 = st.columns(2)
    types = f1.multiselect("Customer type ", sorted(cust["Type"].unique()))
    only = f2.radio("Show", ["All", "Growth", "Loss", "Changed only"], horizontal=True)
    v = cust if not types else cust[cust["Type"].isin(types)]
    if only == "Growth":
        v = v[v["Change"] > 0.005]
    elif only == "Loss":
        v = v[v["Change"] < -0.005]
    elif only == "Changed only":
        v = v[v["Change"].abs() > 0.005]
    st.dataframe(v.style.map(color_change, subset=["Change"])
                 .format({**{m: money for m in months}, "Change": money, "Change %": lambda x: "new" if x is None or pd.isna(x) else f"{x:+.1%}"}),
                 hide_index=True, width="stretch", height=600,
                 column_config={m: month_label(m) for m in months})
    st.download_button("Download as CSV", safe_csv(v), f"trend-{first}-to-{last}.csv", "text/csv")

# -------------------------------------------------------------- Data status --
else:
    st.title("Data status")
    runs = pd.read_sql("SELECT started_at, finished_at, status, message FROM runs ORDER BY id DESC LIMIT 30", con)
    st.subheader("Recent data collections")
    st.dataframe(runs, hide_index=True, width="stretch")
    st.subheader("Usage reports stored")
    st.dataframe(pd.read_sql("SELECT month, line_count, fetched_at FROM billing_months ORDER BY month DESC", con),
                 hide_index=True, width="stretch")
    snaps = con.execute("SELECT COUNT(DISTINCT snap_date) n, MIN(snap_date) a, MAX(snap_date) b FROM license_snapshots").fetchone()
    st.write(f"Daily license snapshots: **{snaps['n']}** days ({snaps['a']} to {snaps['b']}). "
             f"History older than {config.RETENTION_MONTHS} months is removed automatically.")

footer()
