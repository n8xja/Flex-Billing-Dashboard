"""Starts the web dashboard with the chosen appearance (THEME in .env).

THEME=auto   follows each viewer's device setting (light or dark)
THEME=light  always light
THEME=dark   always dark
"""
import os
import sys

from . import config


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    args = ["streamlit", "run", os.path.join(here, "dashboard.py")]
    if config.THEME in ("light", "dark"):
        args += ["--theme.base", config.THEME]
    sys.stdout.flush()
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
