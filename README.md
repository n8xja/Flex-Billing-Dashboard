# Flex Billing Dashboard for Sophos Central partners

A small, self-hosted web dashboard that helps Sophos Central MSP partners close the gap between what Sophos bills them for MSP Flex (usage-based) licensing and what they charge their own customers.

It reads your partner account through the Sophos Central API (**read-only**), keeps up to 24 months of history in a local database, and shows you where quantities have changed since the last bill.

> **Not affiliated with Sophos.** This is an independent community project. Sophos and Sophos Central are trademarks of Sophos Ltd. Nothing here is supported or endorsed by Sophos.

## What it shows

| Page | What you get |
|---|---|
| **Flex changes** | The latest monthly usage report compared with today's live license counts, per customer and product, with the monthly dollar impact. Use it before your distributor's billing day to adjust customer invoices. Covers per-user/server products and firewall subscriptions (matched by serial number). |
| **Firewalls** | Firewall licensing exceptions: a Flex subscription alongside an active term license (paying twice), billed while offline, connected with no protection, stale Flex subscriptions, billed but not managed in Central. HA standby units count as covered when their primary is licensed. |
| **Trends** | Monthly billing by product line and by customer over 3, 6, 12 or 24 months, with growth in green and loss in red. Optional combined call-outs for groups of related tenants. Product renames (e.g. MDR Complete → MDR Plus) are shown as moves, not as a loss plus a gain. |
| **Data status** | Collection history and the monthly reports stored. |

Everything can be renamed and branded (dashboard name, company name, logo, icon, accent colour, footer, labels) from one settings file. See **[CUSTOMIZING.md](CUSTOMIZING.md)**.

## Install

**[INSTALL.md](INSTALL.md)** walks through it step by step for people who have never used Linux or Docker. It covers Rocky Linux 9/10 (and other Red Hat family) and Ubuntu 22.04/24.04. Plan on about an hour, mostly waiting.

You need:
- a Linux server with Docker (the guide installs it),
- a **read-only** Sophos Central Partner API credential,
- a web browser on the same network.

## How it works

| Container | Job |
|---|---|
| `collector` | Python. Reads the Sophos Partner API daily at `COLLECT_HOUR`, or when *Collect fresh data now* is pressed. Stores everything in SQLite (`data/sophos.db`). Keeps `RETENTION_MONTHS` of history. |
| `web` | Streamlit dashboard with local sign-in (bcrypt password hashes in `data/users.json`). Has no access to the Sophos secret. |
| `proxy` | nginx. HTTPS on 443, redirects 80 → 443. Creates a self-signed certificate in `certs/` on first start; drop in your own certificate to replace it. |

Folder mounts carry `:z` so they work with SELinux enforcing (Rocky/RHEL); Docker ignores it where SELinux is off.

Sophos API calls used (all read-only): `whoami`, `partner/v1/tenants`, `partner/v1/billing/usage/{year}/{month}`, `licenses/v1/licenses` (per tenant), `licenses/v1/licenses/firewalls` (partner), `firewall/v1/firewalls` (per tenant, regional host).

## Notes on the numbers

- Prices come from the Sophos usage report (Sophos's price to you, not your price to customers). A product that wasn't on the last report uses the typical price other customers pay for it, and is labeled as an estimate.
- A firewall that hasn't reported to Sophos for `FIREWALL_STALE_DAYS` (default 35) is counted as not live. Sophos may keep billing a unit for a few weeks after it stops reporting, so these are marked "may drop off the next bill".
- Firewall serials are matched regardless of letter case.
- The dashboard is a planning aid. Always check the official usage report before invoicing.

## Your data stays yours

- Your API secret lives only in `.env` on your server, which `.gitignore` keeps out of Git.
- Collected data (`data/`), certificates (`certs/`) and your branding files (`branding/`) are also ignored by Git.
- The project sends nothing anywhere except to the Sophos API, and Streamlit's usage statistics are switched off.

See [SECURITY.md](SECURITY.md) for reporting security issues.

## Contributing

Issues and pull requests are welcome. **Never include real customer names, tenant IDs, serial numbers, API credentials or screenshots of real data** in issues, pull requests or test files. Use made-up examples.

Developer quick start:

```
pip install -r requirements.txt
export DATA_DIR=./data SOPHOS_CLIENT_ID=... SOPHOS_CLIENT_SECRET=...
python -m app.collector --once
python -m app.users add me
streamlit run app/dashboard.py
```

## License

MIT. See [LICENSE](LICENSE).
