"""Small read-only client for the Sophos Central Partner API."""
import time
import requests

from . import config

ID_URL = "https://id.sophos.com/api/v2/oauth2/token"
GLOBAL = "https://api.central.sophos.com"


class SophosError(Exception):
    pass


class Sophos:
    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id or config.SOPHOS_CLIENT_ID
        self.client_secret = client_secret or config.SOPHOS_CLIENT_SECRET
        if not self.client_id or not self.client_secret:
            raise SophosError("SOPHOS_CLIENT_ID and SOPHOS_CLIENT_SECRET must be set in the .env file")
        self.session = requests.Session()
        self._token = None
        self._token_expires = 0
        self.partner_id = None

    # ---- auth -------------------------------------------------------------
    def token(self):
        if self._token and time.time() < self._token_expires - 120:
            return self._token
        r = self.session.post(ID_URL, data={
            "grant_type": "client_credentials", "client_id": self.client_id,
            "client_secret": self.client_secret, "scope": "token"}, timeout=30)
        if r.status_code != 200:
            raise SophosError(f"Sign-in to Sophos failed ({r.status_code}): {r.text[:200]}")
        d = r.json()
        self._token = d["access_token"]
        self._token_expires = time.time() + int(d.get("expires_in", 3600))
        return self._token

    def whoami(self):
        d = self._get(f"{GLOBAL}/whoami/v1", {})
        if d.get("idType") != "partner":
            raise SophosError(f"These credentials are for a {d.get('idType')}, not a partner")
        self.partner_id = d["id"]
        return d

    # ---- http -------------------------------------------------------------
    def _get(self, url, headers, params=None, missing_ok=(404,)):
        for attempt in range(8):
            h = {"Authorization": f"Bearer {self.token()}", **headers}
            try:
                r = self.session.get(url, headers=h, params=params, timeout=120)
            except requests.RequestException as e:
                if attempt == 7:
                    raise SophosError(f"Network error calling {url}: {e}")
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(min(30, 2 * (attempt + 1)))
                continue
            if r.status_code == 401:
                self._token = None
                continue
            if r.status_code in missing_ok:
                return None
            if r.status_code != 200:
                raise SophosError(f"{url} returned {r.status_code}: {r.text[:200]}")
            return r.json()
        raise SophosError(f"Gave up calling {url} after repeated rate limits/errors")

    def _partner(self):
        if not self.partner_id:
            self.whoami()
        return {"X-Partner-ID": self.partner_id}

    # ---- partner-level ----------------------------------------------------
    def tenants(self):
        out, page = [], 1
        while True:
            d = self._get(f"{GLOBAL}/partner/v1/tenants", self._partner(),
                          {"pageTotal": "true", "pageSize": 100, "page": page})
            out += d.get("items", [])
            if page >= d.get("pages", {}).get("total", 1):
                return out
            page += 1

    def billing_usage(self, year, month):
        """Monthly usage report (what the distributor bills from). None if not published yet."""
        out, key = [], None
        while True:
            params = {"pageSize": 1000}
            if key:
                params["pageFromKey"] = key
            d = self._get(f"{GLOBAL}/partner/v1/billing/usage/{year}/{month}", self._partner(), params)
            if d is None:
                return None if not out else out
            out += d.get("items", [])
            key = d.get("pages", {}).get("nextKey")
            if not key:
                return out

    def firewall_licenses(self):
        out, key = [], None
        while True:
            params = {"pageSize": 500}
            if key:
                params["pageFromKey"] = key
            d = self._get(f"{GLOBAL}/licenses/v1/licenses/firewalls", self._partner(), params)
            out += (d or {}).get("items", [])
            key = (d or {}).get("pages", {}).get("nextKey")
            if not key:
                return out

    # ---- tenant-level -----------------------------------------------------
    def tenant_licenses(self, tenant_id):
        d = self._get(f"{GLOBAL}/licenses/v1/licenses", {"X-Tenant-ID": tenant_id}, missing_ok=(403, 404))
        return (d or {}).get("licenses", [])

    def tenant_firewalls(self, tenant_id, api_host):
        out, page = [], 1
        while True:
            # 403: the tenant has no firewall management; treat as no firewalls
            d = self._get(f"{api_host}/firewall/v1/firewalls", {"X-Tenant-ID": tenant_id},
                          {"pageSize": 100, "page": page, "pageTotal": "true"}, missing_ok=(403, 404))
            if not d:
                return out
            out += d.get("items", [])
            if page >= d.get("pages", {}).get("total", 1):
                return out
            page += 1
