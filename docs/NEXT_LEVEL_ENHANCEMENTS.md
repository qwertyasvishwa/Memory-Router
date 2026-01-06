# Next-Level Enhancements (Backlog)

This file tracks missing features and high-impact upgrades to push the Tools + collateral system to a “next level” experience.

## Missing / incomplete today

- No UI to create/edit brand configs (`app/static/brands/<brand>/brand.json`) from the browser.
- No validation/preview warnings for incomplete brand configs (missing logo, bad colors, missing contact fields).
- Collateral pack templates are fixed (no per-brand template overrides or template versioning).
- No PDF export pipeline for print assets (currently HTML print/export).
- No “one-click zip download” for generated packs.
- No SharePoint publish workflow (generated collaterals are local static files only).

## High-impact upgrades

- **Brand manager UI**
  - CRUD brands, upload logos, validate schema, preview tokens, manage contacts.
- **Template system**
  - Versioned templates (v1/v2), per-brand overrides, and safe migration tooling.
- **Exports**
  - Server-side PDF generation for business cards + letterheads, with crop marks/bleed options.
  - Zip bundling of the whole pack (and optional watermark-free assets).
- **Design QA**
  - Add a “visual QA checklist” page that flags spacing/ratio mismatches and missing assets.
  - Snapshot tests for HTML/CSS (e.g., Playwright screenshots) for pixel regression.
- **Copy + tone governance**
  - Introduce a `voice` section in brand config (tone, words to avoid, canonical phrases).
  - Add a “copy lint” step for headlines/taglines used in templates.
- **More generators under Tools**
  - Product spotlight posts, values posts, collections, festival/season packs, retailer POS kits.
  - A generic “campaign pack” generator that bundles social + print templates per campaign.
- **Publishing workflows**
  - Push generated packs to SharePoint with a consistent folder convention + change log.
  - Add approval gating and history (who generated, when, and what changed).

## Recommended next templates

- Product label spec sheet (print)
- Retail shelf talker (A5/A4)
- WhatsApp share card (1080×1350)
- Pitch deck cover slide (16:9)

