# Collateral System (Brand-Agnostic)

This repo includes a deterministic collateral generator designed to keep **tone, spacing, and visual quality consistent** across brands.

## Where it lives

- Tools UI: `/tools/collaterals`
- Output (static): `app/static/generated/<brand>/collateral/`
- Brand config: `app/static/brands/<brand>/brand.json`

The generated output is intentionally re-generatable and should not be hand-edited. Update the brand config instead.

## Brand config schema (minimum)

Create `app/static/brands/<brand>/brand.json`:

```json
{
  "id": "your-brand",
  "name": "Your Brand",
  "tagline": "Short, premium line.",
  "website": "www.example.com",
  "logoUrl": "/static/your-brand/brand/logo.png",
  "theme": {
    "background0": "#fbf9f5",
    "background1": "#efe8df",
    "ink": "#2c2416",
    "muted": "rgba(92, 82, 68, 0.82)",
    "accent": "#d76c2f",
    "accent2": "#4f8b2c"
  },
  "badges": ["Pillar 1", "Pillar 2", "Pillar 3"],
  "contact": {
    "personName": "[Your Name]",
    "personTitle": "[Your Title]",
    "email": "contact@example.com",
    "phone": "+00 00000 00000",
    "location": "Your City, Country",
    "address": ""
  }
}
```

Notes:
- `badges` is capped to 3 for consistent layouts.
- Colors should be hex where possible for predictable rendering in print preview.

## Consistency rules (the “taste”)

These rules are baked into the templates; keep them unchanged unless you want to globally change the style across all brands.

- Layout: use a strict grid; align edges; avoid uneven padding.
- Typography: system font stack; heavy weights only for headings; muted body copy.
- Color: accents are for dividers, badges, and key emphasis; avoid large saturated fills.
- Spacing: prefer fewer elements with more breathing room over dense layouts.
- Copy: short, confident, premium; avoid noisy emoji-heavy decoration unless required by brand.

## What gets generated

- Business card (front): `business-card-front.html` (3.5×2 in)
- Business card (back): `business-card-back.html` (3.5×2 in)
- Letterhead: `letterhead.html` (A4)
- Email signature: `email-signature.html` (table layout for compatibility)
- Brand sheet: `brand-sheet.html` (web preview)
- Pack index: `index.html` (gallery + downloads)

