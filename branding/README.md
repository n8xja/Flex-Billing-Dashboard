# Branding folder

Put your own logo and icon files here, then name them in `.env`:

    BRAND_LOGO=logo.png
    BRAND_ICON=favicon.png

- **Logo:** PNG, JPG or SVG, roughly 400 × 100 pixels (wide rather than tall). It appears at the top of the sidebar.
- **Icon:** a small square PNG (64 × 64 is plenty), shown in the browser tab. You can use an emoji instead: `BRAND_ICON=📊`

Files in this folder are **not** uploaded to GitHub (see `.gitignore`), so your branding stays private. Only this README is.

After adding or changing a file, restart: `bash stop.sh` then `bash start.sh`.
