# Shopify CLI (Themes) Cheatsheet

A practical reference for **local Liquid theme development** plus how to **push / publish** updates to a remote Shopify store.

---

## 0) Quick sanity commands

```bash
shopify version
shopify help
shopify commands
```

---

## 1) Auth / connect to the right store

```bash
shopify auth login
shopify auth logout
```

Tip: if you get weird “wrong store” behavior, a logout + login is often the quickest reset.

---

## 2) Create or download a theme locally

### Start a new theme (starter)

```bash
shopify theme init
```

### Pull an existing theme from the store

```bash
shopify theme pull --store your-store.myshopify.com
# optionally target a specific theme:
shopify theme pull --store your-store.myshopify.com --theme <THEME_ID_OR_NAME>
```

Useful pull flags (common):
- `--live` (pull the live theme)
- `--development`
- `--only "..."`
- `--ignore "..."`
- `--nodelete`

---

## 3) Local development with hot reload

```bash
shopify theme dev --store your-store.myshopify.com
# common options:
shopify theme dev --store your-store.myshopify.com --open
shopify theme dev --store your-store.myshopify.com --live-reload full-page
shopify theme dev --host 0.0.0.0 --port 9292
```

Notes:
- `theme dev` uploads to (or replaces) a **development theme** and provides preview + editor links.

---

## 4) List themes / double-check your target

```bash
shopify theme list --store your-store.myshopify.com
shopify theme info --store your-store.myshopify.com --theme <THEME_ID_OR_NAME>
```

Use `theme list` to grab the theme ID; `theme info` to verify before pushing.

---

## 5) Push your local changes to the remote store (deploy)

### A) Safest workflow: push to a NEW unpublished theme (QA/staging)

```bash
shopify theme push
```

### B) Push to an existing theme (overwrite that theme)

```bash
shopify theme push --store your-store.myshopify.com --theme <THEME_ID_OR_NAME>
```

### C) Push ONLY certain files (surgical deploy)

```bash
shopify theme push --store your-store.myshopify.com --theme <THEME_ID> --only "sections/*.liquid"
```

### D) Avoid overwriting merchant-edited JSON/data files

Merchants often change:
- `config/settings_data.json`
- JSON templates in `templates/*.json`

You can ignore them during deploy:

```bash
shopify theme push --store your-store.myshopify.com --theme <THEME_ID> \
  --ignore "config/settings_data.json" \
  --ignore "templates/*.json"
```

---

## 6) Publish (make it the LIVE theme)

### Option 1: publish an unpublished theme

```bash
shopify theme publish --store your-store.myshopify.com --theme <THEME_ID>
# optional:
shopify theme publish --store your-store.myshopify.com --theme <THEME_ID> --force
```

### Option 2: push and publish (one-liner)

```bash
shopify theme push --store your-store.myshopify.com --theme <THEME_ID> --publish
```

⚠️ If pushing directly to the live theme, you may need:

```bash
shopify theme push --store your-store.myshopify.com --theme <LIVE_THEME_ID> --allow-live
```

---

## 7) Share / preview links for clients

### Create an unpublished theme + shareable preview link

```bash
shopify theme share --store your-store.myshopify.com
```

### Open preview/editor links for a theme

```bash
shopify theme open --store your-store.myshopify.com --theme <THEME_ID>
```

---

## 8) Quality + safety checks (before pushing)

### Theme linting (Theme Check)

```bash
shopify theme check
```

### Require checks to pass before pushing

```bash
shopify theme push --strict
```

---

## 9) Environments (stop re-typing store/theme)

Create a `shopify.theme.toml` in your project root:

```toml
[environments.dev]
store = "your-store.myshopify.com"
theme = "123456789"
```

Then run:

```bash
shopify theme dev --environment dev
shopify theme push --environment dev
```

---

## Recommended deploy flow (safe + simple)

1) Develop locally

```bash
shopify theme dev --store your-store.myshopify.com
```

2) Push to an unpublished theme for QA

```bash
shopify theme push --store your-store.myshopify.com --unpublished
```

3) When approved, publish that theme

```bash
shopify theme publish --store your-store.myshopify.com --theme <NEW_THEME_ID>
```

