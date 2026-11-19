"""Dashboard sign-in accounts, stored in users.json in the data folder.

Passwords are never stored, only a bcrypt hash of them.

    python -m app.users add <username>       (asks for the password twice)
    python -m app.users remove <username>
    python -m app.users list
"""
import getpass
import json
import logging
import os
import sys
import threading
import time
from collections import defaultdict, deque

import bcrypt

from . import config

MIN_LENGTH = 12
MAX_BYTES = 72  # bcrypt only uses the first 72 bytes of a password

log = logging.getLogger("signin")
if not log.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)

# A real hash to compare against when the user doesn't exist, so a wrong
# user name takes as long as a wrong password (no user-name guessing by timing).
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt())


def load():
    try:
        if config.USERS_FILE.exists():
            return json.loads(config.USERS_FILE.read_text())
    except (OSError, ValueError):
        log.error("users file could not be read: %s", config.USERS_FILE)
    return {}


def save(users):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = config.USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(config.USERS_FILE)


def check(username, password):
    """True if the user name and password match. No throttling (see attempt())."""
    pw = (password or "").encode()
    u = load().get((username or "").strip().lower())
    if not u or len(pw) > MAX_BYTES:
        bcrypt.checkpw(b"x", _DUMMY_HASH)  # same timing as a real check
        return False
    try:
        return bcrypt.checkpw(pw, u["hash"].encode())
    except (ValueError, KeyError):
        return False


# --------------------------------------------------------- sign-in throttle --
# Shared by every browser session in this process, so opening a new tab or
# session does not reset the count (the old per-session counter could be
# bypassed that way).
class _Throttle:
    def __init__(self):
        self.lock = threading.Lock()
        self.by_user = defaultdict(deque)   # user name -> times of recent failures
        self.by_ip = defaultdict(deque)     # client address -> times of recent failures
        self.locked_until = {}              # user name -> time the lock ends

    @staticmethod
    def _trim(q, now, window):
        while q and now - q[0] > window:
            q.popleft()

    def blocked(self, user, ip):
        """Seconds the caller must wait before trying again, or 0."""
        now = time.time()
        with self.lock:
            until = self.locked_until.get(user, 0)
            if until > now:
                return int(until - now) + 1
            q = self.by_ip[ip]
            self._trim(q, now, 60)
            if len(q) >= config.SIGNIN_MAX_PER_IP_PER_MINUTE:
                return int(60 - (now - q[0])) + 1
        return 0

    def failed(self, user, ip):
        now = time.time()
        window = config.SIGNIN_LOCKOUT_MINUTES * 60
        with self.lock:
            q = self.by_user[user]
            q.append(now)
            self._trim(q, now, window)
            self.by_ip[ip].append(now)
            if len(q) >= config.SIGNIN_MAX_FAILURES:
                self.locked_until[user] = now + window
                q.clear()
                return True
        return False

    def succeeded(self, user):
        with self.lock:
            self.by_user.pop(user, None)
            self.locked_until.pop(user, None)


_throttle = _Throttle()


def attempt(username, password, ip="unknown"):
    """Check a sign-in with brute-force protection.

    Returns (ok, message). Failed attempts are logged (user name and address,
    never the password) so they show up in `docker compose logs web`.
    """
    user = (username or "").strip().lower()[:100]
    wait = _throttle.blocked(user, ip)
    if wait:
        log.warning("sign-in refused while locked: user=%r ip=%s", user, ip)
        return False, f"Too many failed sign-ins. Please wait {max(1, round(wait / 60))} minute(s) and try again."
    ok = check(user, password)
    if ok:
        _throttle.succeeded(user)
        log.info("sign-in ok: user=%r ip=%s", user, ip)
        return True, ""
    locked = _throttle.failed(user, ip)
    log.warning("sign-in failed: user=%r ip=%s%s", user, ip, " (now locked)" if locked else "")
    if locked:
        return False, (f"Too many failed sign-ins. This user name is locked for "
                       f"{config.SIGNIN_LOCKOUT_MINUTES} minutes.")
    return False, "That user name and password did not match."


# ------------------------------------------------------------- management --
def set_password(username, password):
    users = load()
    users[username.strip().lower()] = {"hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()}
    save(users)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("add", "remove", "list"):
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        names = sorted(load())
        print("\n".join(names) if names else "No users yet.")
        return
    if len(sys.argv) < 3:
        print(f"Please give a user name, for example:  {cmd} owner")
        sys.exit(1)
    name = sys.argv[2].strip().lower()
    if not name or len(name) > 100 or any(c.isspace() for c in name):
        print("User names must be 1 to 100 characters with no spaces.")
        sys.exit(1)
    if cmd == "remove":
        users = load()
        if users.pop(name, None) is None:
            print(f"There is no user called {name}.")
            sys.exit(1)
        save(users)
        print(f"Removed {name}.")
        return
    while True:
        p1 = getpass.getpass(f"New password for {name} ({MIN_LENGTH} to {MAX_BYTES} characters; nothing shows as you type): ")
        if len(p1) < MIN_LENGTH:
            print(f"That is shorter than {MIN_LENGTH} characters. Please try again.")
            continue
        if len(p1.encode()) > MAX_BYTES:
            print(f"That is longer than {MAX_BYTES} characters (accented letters and symbols can count double). Please try again.")
            continue
        if getpass.getpass("Type the same password again: ") != p1:
            print("The two passwords did not match. Please try again.")
            continue
        break
    set_password(name, p1)
    print(f"Saved. {name} can now sign in to the dashboard.")


if __name__ == "__main__":
    main()
