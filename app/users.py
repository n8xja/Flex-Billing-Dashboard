"""Dashboard sign-in accounts, stored in users.json in the data folder.

Passwords are never stored, only a bcrypt hash of them.

    python -m app.users add <username>       (asks for the password twice)
    python -m app.users remove <username>
    python -m app.users list
"""
import getpass
import json
import os
import sys

import bcrypt

from . import config

MIN_LENGTH = 12


def load():
    if config.USERS_FILE.exists():
        return json.loads(config.USERS_FILE.read_text())
    return {}


def save(users):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = config.USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(config.USERS_FILE)


def check(username, password):
    u = load().get((username or "").strip().lower())
    if not u:
        bcrypt.checkpw(b"x", bcrypt.hashpw(b"y", bcrypt.gensalt()))  # same timing as a real check
        return False
    return bcrypt.checkpw(password.encode(), u["hash"].encode())


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
    if cmd == "remove":
        users = load()
        if users.pop(name, None) is None:
            print(f"There is no user called {name}.")
            sys.exit(1)
        save(users)
        print(f"Removed {name}.")
        return
    while True:
        p1 = getpass.getpass(f"New password for {name} (at least {MIN_LENGTH} characters; nothing shows as you type): ")
        if len(p1) < MIN_LENGTH:
            print(f"That is shorter than {MIN_LENGTH} characters. Please try again.")
            continue
        if getpass.getpass("Type the same password again: ") != p1:
            print("The two passwords did not match. Please try again.")
            continue
        break
    set_password(name, p1)
    print(f"Saved. {name} can now sign in to the dashboard.")


if __name__ == "__main__":
    main()
