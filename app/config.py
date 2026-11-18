"""Settings, read from environment variables (set in the .env file).

Every setting has a neutral default. See CUSTOMIZING.md for what each one does.
"""
import os
from pathlib import Path


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def _list(name, default=""):
    return [p.strip() for p in _env(name, default).split(",") if p.strip()]


# ------------------------------------------------------------- storage --
DATA_DIR = Path(_env("DATA_DIR", "/data"))
DB_PATH = DATA_DIR / "sophos.db"
USERS_FILE = DATA_DIR / "users.json"
REFRESH_FLAG = DATA_DIR / "refresh-requested"
BRANDING_DIR = Path(_env("BRANDING_DIR", "/branding"))

# --------------------------------------------------------- Sophos API --
SOPHOS_CLIENT_ID = _env("SOPHOS_CLIENT_ID")
SOPHOS_CLIENT_SECRET = _env("SOPHOS_CLIENT_SECRET")

# ------------------------------------------------------------ schedule --
COLLECT_HOUR = int(_env("COLLECT_HOUR", "6"))          # 0-23, server local time (TZ)
RETENTION_MONTHS = int(_env("RETENTION_MONTHS", "24"))
FIREWALL_STALE_DAYS = int(_env("FIREWALL_STALE_DAYS", "35"))

# Day of the month your distributor (or Sophos) counts MSP Flex usage.
BILLING_DAY = int(_env("BILLING_DAY", "22"))

# ------------------------------------------------------------ branding --
BRAND_NAME = _env("BRAND_NAME", "Flex Billing Dashboard")
BRAND_ORG = _env("BRAND_ORG")                  # your company name, shown in the sidebar
BRAND_TAGLINE = _env("BRAND_TAGLINE")          # short line under the sign-in title
BRAND_FOOTER = _env("BRAND_FOOTER")            # e.g. "Questions? support@example.com"
BRAND_LOGO = _env("BRAND_LOGO")                # file name inside the branding folder
BRAND_ICON = _env("BRAND_ICON", "🛡️")          # emoji, or file name inside the branding folder
# BRAND_COLOR is applied by docker-compose as Streamlit's theme colour.


def branding_file(name):
    """Full path of a readable file in the branding folder, or None.

    Never raises: a missing, unreadable or oddly named file (or an emoji such
    as the default icon) just means "no file", and the dashboard carries on.
    """
    if not name or "/" in name or "\\" in name:
        return None
    try:
        p = (BRANDING_DIR / name).resolve()
        p.relative_to(BRANDING_DIR.resolve())  # stay inside the branding folder
        if p.is_file() and os.access(p, os.R_OK):
            return p
    except (OSError, ValueError):
        pass
    return None


# --------------------------------------------------------------- labels --
# What each Sophos tenant billing type is called on screen.
LABEL_FLEX = _env("LABEL_FLEX", "Flex")    # Sophos "usage" billing
LABEL_TERM = _env("LABEL_TERM", "Term")
LABEL_TRIAL = _env("LABEL_TRIAL", "Trial")
TYPE_LABELS = {"usage": LABEL_FLEX, "term": LABEL_TERM, "trial": LABEL_TRIAL}

# ------------------------------------------------------------- analysis --
# Customer name prefixes that get a combined call-out on the Trends page,
# comma separated, e.g. "Acme,Contoso". Empty = no call-outs.
GROUP_PREFIXES = _list("GROUP_PREFIXES")

# Product renames/migrations to show as "Moved X → Y" instead of a loss plus a gain.
# Format: "Old>New;Old>New". Names are as they appear after shortening (no "Sophos ").
PRODUCT_MOVES = [tuple(x.split(">", 1)) for x in
                 _env("PRODUCT_MOVES", "MDR Complete>MDR Plus;MDR Essentials>MDR").split(";") if ">" in x]


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
