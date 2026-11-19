# Customizing the dashboard

Almost everything can be changed **without touching any code**, by editing one settings file (`.env`) and, for logos, dropping files into the `branding` folder. Part 1 covers those settings. Part 2 is for people comfortable editing Python.

Your settings and branding files are **never uploaded to GitHub** (`.gitignore` blocks them), so you can share or update the project without exposing anything about your business.

---

## Part 1: Settings anyone can change

### How to change a setting

1. Connect to the server and go to the project folder (INSTALL.md, step 3):
   ```
   cd Flex-Billing-Dashboard
   ```
2. Open the settings file:
   ```
   nano .env
   ```
3. Use the arrow keys to find the line, change the text after the `=` sign, then save with **Ctrl + O**, **Enter**, and exit with **Ctrl + X**.
4. Restart so the change takes effect:
   ```
   bash stop.sh
   bash start.sh
   ```

**Rules for the settings file:** one setting per line, no spaces around the `=`, and a line starting with `#` is a note that's ignored. To leave a setting empty, put nothing after the `=`.

### Branding

| Setting | What it changes | Example |
|---|---|---|
| `BRAND_NAME` | The dashboard's name: browser tab, sign-in page, titles | `BRAND_NAME=Acme License Desk` |
| `BRAND_ORG` | Your company name, at the top of the sidebar | `BRAND_ORG=Acme IT Services` |
| `BRAND_TAGLINE` | A short line under the title on the sign-in page | `BRAND_TAGLINE=Internal billing tool` |
| `BRAND_FOOTER` | Small text at the bottom of each page | `BRAND_FOOTER=Questions? billing@acme.example` |
| `BRAND_LOGO` | A logo at the top of the sidebar (see below) | `BRAND_LOGO=logo.png` |
| `BRAND_ICON` | The little picture in the browser tab: an emoji or an image file | `BRAND_ICON=📊` or `BRAND_ICON=favicon.png` |
| `BRAND_COLOR` | Accent colour for buttons and highlights, as a hex code in quotes | `BRAND_COLOR="#0f766e"` |
| `THEME` | The starting appearance for someone who hasn't chosen one yet. `auto` follows their device (dark if their computer is set to dark mode); `light` or `dark` starts everyone in that mode. Each person can still switch (see below). | `THEME=dark` |

Leave any of the optional ones empty to hide it.

**Adding a logo or icon file:**

1. Make the image on your own computer:
   - **Logo:** PNG, JPG or SVG, wide rather than tall (about 400 × 100 pixels).
   - **Icon:** a small square PNG (64 × 64 pixels is plenty).
2. Copy it into the `branding` folder inside the project on the server. A file-copy tool such as **WinSCP** (Windows) or **Cyberduck** (Mac) works well; connect with the same server address, user name and password you use for `ssh`.
3. Put the file's name (just the name, not a folder) in `.env`, for example `BRAND_LOGO=logo.png`.
4. Restart (`bash stop.sh`, then `bash start.sh`).

> **How people switch between light and dark:** open the menu **⋮** at the top right of the dashboard and choose a theme. The choice is saved in that web browser, so it's still there at the next sign-in. It's remembered per browser and computer, not per user name: a different computer starts from `THEME` again, and two people sharing one browser share the choice. (The dashboard is built on Streamlit, which only lets the browser change the theme, not the app itself.) Both themes use your `BRAND_COLOR`.

> **Dark mode tips:** pick a `BRAND_COLOR` that stands out on both white and near-black backgrounds (mid-tones such as `#2563eb` or `#0f766e` work well). For the logo, a PNG with a transparent background looks right in both modes.

> **Finding a hex colour code:** search the web for "color picker", choose a colour, and copy the code that starts with `#`. Keep the quotes: `BRAND_COLOR="#0f766e"`.

### Labels

Sophos tenants are billed one of three ways. You can rename how each appears on screen, for example to match the words your team uses:

| Setting | Sophos billing type | Default |
|---|---|---|
| `LABEL_FLEX` | usage (MSP Flex) | `Flex` |
| `LABEL_TERM` | term | `Term` |
| `LABEL_TRIAL` | trial | `Trial` |

`LABEL_FLEX` also renames the **Flex changes** page and the matching headings.

### Billing and schedule

| Setting | What it does | Default |
|---|---|---|
| `TZ` | Your time zone, so the daily run happens at the right local hour. Use a name from the [time zone list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones), such as `America/Chicago` or `Europe/London`. | `UTC` |
| `COLLECT_HOUR` | Hour of the day (0 to 23) for the daily data collection | `6` |
| `BILLING_DAY` | Day of the month your distributor counts MSP Flex usage. Used in page wording and month labels. | `22` |
| `RETENTION_MONTHS` | How many months of history to keep. Older data is deleted automatically. | `24` |

### Analysis

| Setting | What it does | Default |
|---|---|---|
| `GROUP_PREFIXES` | Groups of tenants to total together on the Trends page. Any customer whose name **starts with** one of these words is included in that group. Separate several with commas. Each group gets a combined call-out, a per-tenant breakout with costs, and a license-counts table with **no costs**, each with a **Download as CSV** button. The cost-free one is meant for sending to the customer. The individual tenants still appear in the full customer list. | empty (no groups) |
| `PRODUCT_MOVES` | Product changes to show as *"Moved X → Y"* rather than a loss and a gain. Format: `Old>New;Old>New`, using the product names as the dashboard shows them (without "Sophos "). | `MDR Complete>MDR Plus;MDR Essentials>MDR` |
| `FIREWALL_STALE_DAYS` | Days a firewall can go without reporting to Sophos before it stops counting as live | `35` |

**Example of groups:** if you manage many small tenants named `Acme: Branch A`, `Acme: Branch B` and so on, and others named `Contoso - North` and `Contoso - South`:

```
GROUP_PREFIXES=Acme,Contoso
```

### Sign-in security

| Setting | What it does | Default |
|---|---|---|
| `SESSION_TIMEOUT_MINUTES` | Signs a person out after this many minutes without using the dashboard | `120` |
| `SIGNIN_MAX_FAILURES` | Wrong passwords in a row before that user name is locked | `5` |
| `SIGNIN_LOCKOUT_MINUTES` | How long a locked user name stays locked | `15` |
| `SIGNIN_MAX_PER_IP_PER_MINUTE` | Wrong passwords allowed per minute from one computer, whatever user name is tried | `10` |
| `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS` | Set to `type` to hide technical error details (tracebacks) from viewers. They still appear in `sudo docker compose logs web`. Leave unset while you're setting things up, since the details help with troubleshooting. | unset |

Sign-ins, sign-outs, failed attempts and locks are written to the web log with the user name and computer address (never the password). To see them:

```
sudo docker compose logs web | grep sign
```

### Web address and certificate

| Setting | What it does | Default |
|---|---|---|
| `SERVER_NAME` | The name people type in the browser. Used in the self-signed certificate. | `billing-dashboard` |
| `HTTPS_PORT` | The port for the secure web page | `443` |
| `HTTP_PORT` | The plain-HTTP port. It only redirects visitors to the secure page, keeping the port number. | `80` |
| `LISTEN_ADDRESS` | Listen on only one of the server's IP addresses, e.g. `10.0.0.25`. Useful on servers with more than one network card. Leave empty to listen on all of them. | empty |

**Changing a port, step by step** (example: moving the dashboard to 8443 because something else uses 443):

1. `nano .env`, change `HTTPS_PORT=443` to `HTTPS_PORT=8443`, save (**Ctrl + O**, **Enter**) and exit (**Ctrl + X**).
2. Restart: `bash stop.sh`, then `bash start.sh`. The message at the end shows the new address, e.g. `https://10.0.0.25:8443`.
3. Let the new port through the server's firewall: `bash open-firewall.sh`
4. Optional, if nothing else needs the old port: `bash open-firewall.sh --close 443`

From then on, people use the address with the port: `https://10.0.0.25:8443`. Typing `http://10.0.0.25` still works if `HTTP_PORT` is 80; it forwards to the right port automatically.

Pick a port between 1024 and 65535 that nothing else on the server uses, such as 8443 or 9443. INSTALL.md, "Opening ports in the server's firewall", has the full firewall instructions.

If you change `SERVER_NAME` after the first start, delete the old self-signed certificate so a new one is made with the new name:

```
sudo rm certs/server.crt certs/server.key
bash stop.sh
bash start.sh
```

To use a certificate from your own certificate authority instead, see "Later: using a certificate from your own CA" in INSTALL.md.

---

## Part 2: Changing the code (for developers)

The project is plain Python. Everything that runs is in the `app` folder:

| File | What's in it |
|---|---|
| `app/config.py` | Every setting, its default, and the helpers that read them. **Add new settings here.** |
| `app/sophos.py` | The read-only Sophos API client (sign-in, paging, rate-limit retries). |
| `app/collector.py` | What's downloaded each day and how it's stored; history clean-up. |
| `app/db.py` | The SQLite tables. |
| `app/analysis.py` | The calculations behind each page: Flex changes, firewall checks, trends. Returns pandas tables. |
| `app/dashboard.py` | The web pages (Streamlit). |
| `app/users.py` | Sign-in accounts. |

### Common changes

**Add a new setting.** Read it in `app/config.py`, for example `MY_SETTING = _env("MY_SETTING", "default")`, use `config.MY_SETTING` wherever you need it, and add a commented line to `.env.example` so others know it exists. Settings in `.env` reach both containers automatically.

**Change how products are grouped on the Trends page.** Edit `product_line()` in `app/analysis.py`. It receives the product description and group (User, Server, Device) from the usage report and returns the product line name.

**Change the firewall rules.** The checks are in `firewall_exceptions()` in `app/analysis.py`, in priority order. Each one sets a `prio`, an `issue` name and the `action` text shown in **What to do**.

**Add a page.** In `app/dashboard.py`, add the page name to the `st.radio(...)` list in the sidebar and add an `elif page == "...":` block. Put calculations in `app/analysis.py` and keep `dashboard.py` for display. Add a **Download as CSV** button (`st.download_button`) so people can take the data away.

**Change the look further.** Streamlit's theme settings live in `.streamlit/config.toml`. You can also set any Streamlit option from `.env` with a variable named `STREAMLIT_<SECTION>_<OPTION>`, for example `STREAMLIT_THEME_BASE=dark`. That's how `BRAND_COLOR` becomes `STREAMLIT_THEME_PRIMARY_COLOR`.

### Trying changes before you deploy

On any computer with Python 3.12:

```
pip install -r requirements.txt
export DATA_DIR=./data SOPHOS_CLIENT_ID=... SOPHOS_CLIENT_SECRET=...
python -m app.collector --once      # about 10 minutes
python -m app.users add me
streamlit run app/dashboard.py      # opens http://localhost:8501
```

Branding settings work the same way locally: export them, and point `BRANDING_DIR` at a folder with your logo.

### Deploying your changes

If you changed code, commit it to your own copy of the project on GitHub (a fork, or your own repository), then on the server run `bash update.sh`. It pulls the latest version and rebuilds.

If you only changed `.env` or the `branding` folder, just restart (`bash stop.sh`, `bash start.sh`). Nothing needs to go to GitHub.

### Sharing improvements

If you'd like to contribute a change back to the project, open a pull request. Please make sure it contains **no real customer names, tenant IDs, serial numbers, prices from your account, screenshots of real data, or credentials**. Use made-up examples such as "Acme" and "Contoso".
