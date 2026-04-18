# BRAND.md — StoreMD visual identity

## Logo

Source file: `frontend/public/icons/icon-512x512.png` (generated from master `storemd_icon_1200x1200.png`).

## Color palette

- **Brand blue:** `#2563eb` (Tailwind `blue-600`) — logo background, Shopify App Store icon, manifest theme_color
- **Brand green accent:** pulse end dot + "MD" wordmark — pale mint ~`#86efac` (Tailwind `green-300`)
- **Brand white:** pulse line, "Store" wordmark
- **App background:** `#0a0a0f` (deep black, landing and dashboard dark mode)
- **Accent cyan (UI only, not logo):** `#06b6d4` (Tailwind `cyan-500`) — CTAs, gradient emphasis

## Usage

- Logo stays solid blue everywhere — landing, dashboard, Shopify App Store, favicon, PWA, OG image.
- Do **not** recolor the logo. No dark variant. No transparent pulse version. Consistency over color system purity.
- Minimum clear space around the logo = 25% of the logo's short side.
- Minimum size: 32×32 px on screen, 16×16 for favicons.

## File inventory

| Purpose | Path | Size |
|---|---|---|
| Source master | `storemd_icon_1200x1200.png` (repo root) | 1200×1200 |
| Shopify App Store | `frontend/public/shopify-app-icon.png` | 1200×1200 |
| OG / social share | `frontend/public/og-image.png` | 1200×630 |
| Apple touch icon | `frontend/public/apple-touch-icon.png` | 180×180 |
| Favicons | `frontend/public/favicon-{16,32,48}x{16,32,48}.png` + `favicon.ico` | 16/32/48 |
| PWA icons | `frontend/public/icons/icon-{72,96,128,144,152,192,384,512}x{...}.png` | 8 sizes |

## Regeneration

If the master logo changes, replace `storemd_icon_1200x1200.png` at repo root, then:

```bash
cd frontend
npm run generate:logo
npm run generate:og
```
