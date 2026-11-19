"""Starts the web dashboard with the chosen appearance.

Both a light and a dark theme are set up, each in BRAND_COLOR, so people can
switch between them in the menu at the top right of the page. Their browser
remembers the choice for next time. THEME in .env only sets the starting
point for someone who hasn't chosen yet:

THEME=auto   follow the viewer's device setting (light or dark)
THEME=light  start in light
THEME=dark   start in dark
"""
import os
import sys

from . import config


def args():
    here = os.path.dirname(os.path.abspath(__file__))
    a = ["streamlit", "run", os.path.join(here, "dashboard.py"),
         "--theme.light.primaryColor", config.BRAND_COLOR,
         "--theme.dark.primaryColor", config.BRAND_COLOR]
    if config.THEME in ("light", "dark"):
        a += ["--theme.base", config.THEME]
    return a


def main():
    a = args()
    sys.stdout.flush()
    os.execvp(a[0], a)


if __name__ == "__main__":
    main()
