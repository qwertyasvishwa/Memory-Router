from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any

from .brands import load_brand_config


_SAFE_ID_RE = re.compile(r"[^a-z0-9-_]")


def _sanitize_id(value: str) -> str:
    value = (value or "").strip().lower()
    value = _SAFE_ID_RE.sub("", value)
    return value


def _static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"


def _generated_dir(brand_id: str) -> Path:
    safe = _sanitize_id(brand_id)
    if not safe:
        raise ValueError("Invalid brand id")
    return _static_dir() / "generated" / safe / "collateral"


def _brand_defaults(brand_id: str) -> dict[str, Any]:
    return {
        "id": brand_id,
        "name": brand_id,
        "tagline": "Premium. Minimal. Consistent.",
        "website": "",
        "logoUrl": "",
        "theme": {
            "background0": "#fbf9f5",
            "background1": "#efe8df",
            "ink": "#2c2416",
            "muted": "rgba(92, 82, 68, 0.82)",
            "accent": "#d76c2f",
            "accent2": "#4f8b2c",
        },
        "badges": ["Handmade", "Organic", "Fresh"],
        "contact": {
            "personName": "[Your Name]",
            "personTitle": "[Your Title]",
            "email": "contact@example.com",
            "phone": "+00 00000 00000",
            "location": "Your City, Country",
            "address": "",
        },
    }


def _merge_dict(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in (src or {}).items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _merge_dict(dst[key], value)  # type: ignore[index]
        else:
            dst[key] = value
    return dst


def _load_brand(brand_id: str) -> dict[str, Any]:
    safe = _sanitize_id(brand_id)
    config = load_brand_config(safe) or {}
    merged = _brand_defaults(safe)
    _merge_dict(merged, config)
    merged["id"] = safe
    merged["name"] = str(merged.get("name") or safe).strip()
    merged["tagline"] = str(merged.get("tagline") or "").strip()
    merged["website"] = str(merged.get("website") or "").strip()
    merged["logoUrl"] = str(merged.get("logoUrl") or "").strip()
    return merged


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = (value or "").strip()
    if not value.startswith("#"):
        return None
    hex_value = value[1:]
    if len(hex_value) == 3:
        try:
            r = int(hex_value[0] * 2, 16)
            g = int(hex_value[1] * 2, 16)
            b = int(hex_value[2] * 2, 16)
            return (r, g, b)
        except ValueError:
            return None
    if len(hex_value) == 6:
        try:
            r = int(hex_value[0:2], 16)
            g = int(hex_value[2:4], 16)
            b = int(hex_value[4:6], 16)
            return (r, g, b)
        except ValueError:
            return None
    return None


def _rgba(hex_or_unknown: str, alpha: float) -> str:
    rgb = _hex_to_rgb(hex_or_unknown)
    if rgb is None:
        return f"rgba(0, 0, 0, {alpha})"
    r, g, b = rgb
    return f"rgba({r}, {g}, {b}, {alpha})"


def generate_collateral_pack(brand_id: str) -> dict[str, str]:
    """
    Generates a deterministic collateral pack under:
      `app/static/generated/<brand_id>/collateral/*`
    """
    brand = _load_brand(brand_id)
    out_dir = _generated_dir(brand_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    now = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    files: dict[str, str] = {
        "index": "index.html",
        "business_card_front": "business-card-front.html",
        "business_card_back": "business-card-back.html",
        "letterhead": "letterhead.html",
        "email_signature": "email-signature.html",
        "brand_sheet": "brand-sheet.html",
        "manifest": "manifest.json",
    }

    theme = brand.get("theme") or {}
    c = brand.get("contact") or {}
    badges = brand.get("badges") or []
    badges = [str(x).strip() for x in badges if str(x).strip()][:3] or ["Handmade", "Organic", "Fresh"]

    css_vars = {
        "bg0": theme.get("background0") or "#fbf9f5",
        "bg1": theme.get("background1") or "#efe8df",
        "ink": theme.get("ink") or "#2c2416",
        "muted": theme.get("muted") or "rgba(92, 82, 68, 0.82)",
        "accent": theme.get("accent") or "#d76c2f",
        "accent2": theme.get("accent2") or "#4f8b2c",
    }
    css_vars["accent2_10"] = _rgba(str(css_vars["accent2"]), 0.10)
    css_vars["accent2_12"] = _rgba(str(css_vars["accent2"]), 0.12)
    css_vars["accent2_14"] = _rgba(str(css_vars["accent2"]), 0.14)
    css_vars["accent2_28"] = _rgba(str(css_vars["accent2"]), 0.28)
    css_vars["ink_10"] = _rgba(str(css_vars["ink"]), 0.10)
    css_vars["ink_12"] = _rgba(str(css_vars["ink"]), 0.12)
    css_vars["ink_14"] = _rgba(str(css_vars["ink"]), 0.14)

    logo_url = brand.get("logoUrl") or ""
    brand_name = brand.get("name") or brand_id
    tagline = brand.get("tagline") or ""
    website = brand.get("website") or ""
    person_name = c.get("personName") or "[Your Name]"
    person_title = c.get("personTitle") or "[Your Title]"
    email = c.get("email") or "contact@example.com"
    phone = c.get("phone") or "+00 00000 00000"
    location = c.get("location") or "Your City, Country"
    address = c.get("address") or ""

    def write_text(name: str, text: str) -> None:
        (out_dir / name).write_text(text, encoding="utf-8")

    # Business card front
    write_text(
        files["business_card_front"],
        f"""<!doctype html>
<html lang="en">

    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{brand_name} - Business Card (Front)</title>
        <style>
            @page {{
                size: 3.5in 2in;
                margin: 0;
            }}

            :root {{
                --bg0: {css_vars["bg0"]};
                --bg1: {css_vars["bg1"]};
                --ink: {css_vars["ink"]};
                --muted: {css_vars["muted"]};
                --accent: {css_vars["accent"]};
                --accent2: {css_vars["accent2"]};
            }}

            * {{ box-sizing: border-box; }}

            body {{
                margin: 0;
                width: 3.5in;
                height: 2in;
                font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                color: var(--ink);
                overflow: hidden;
            }}

            .card {{
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, var(--bg0), var(--bg1));
                position: relative;
            }}

            .card::before {{
                content: "";
                position: absolute;
                inset: 0;
                background-image: radial-gradient({css_vars["accent2_14"]} 1.5px, transparent 1.5px);
                background-size: 18px 18px;
                opacity: 0.65;
                pointer-events: none;
            }}

            .safe {{
                position: relative;
                z-index: 1;
                width: 100%;
                height: 100%;
                padding: 0.24in;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                gap: 10px;
            }}

            .top {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 10px;
            }}

            .logo {{
                width: 0.96in;
                height: auto;
                display: block;
                filter: drop-shadow(0 10px 18px rgba(0, 0, 0, 0.12));
            }}

            .tagline {{
                margin-top: 8px;
                font-size: 7.5pt;
                font-weight: 650;
                color: var(--muted);
                letter-spacing: 0.02em;
                max-width: 1.6in;
            }}

            .badges {{
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 6px;
            }}

            .badge {{
                font-size: 7pt;
                font-weight: 750;
                padding: 3px 8px;
                border-radius: 999px;
                background: {css_vars["accent2_12"]};
                border: 1.5px solid {css_vars["accent2_28"]};
                color: var(--accent2);
                white-space: nowrap;
            }}

            .name {{
                font-size: 21pt;
                font-weight: 900;
                letter-spacing: -0.03em;
                line-height: 1;
            }}

            .divider {{
                height: 2px;
                width: 42px;
                border-radius: 999px;
                background: var(--accent2);
                opacity: 0.9;
                margin-top: 8px;
            }}

            .meta {{
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                gap: 10px;
                font-size: 8pt;
                color: var(--muted);
                font-weight: 650;
            }}

            .meta a {{
                color: inherit;
                text-decoration: none;
            }}
        </style>
    </head>

    <body>
        <div class="card" role="img" aria-label="{brand_name} business card front">
            <div class="safe">
                <div class="top">
                    <div>
                        {"<img class=\"logo\" src=\"" + logo_url + "\" alt=\"" + brand_name + " logo\">" if logo_url else ""}
                        {"<div class=\"tagline\">" + tagline + "</div>" if tagline else ""}
                    </div>
                    <div class="badges" aria-label="Brand badges">
                        {''.join([f'<div class="badge">{b}</div>' for b in badges])}
                    </div>
                </div>

                <div>
                    <div class="name">{brand_name}</div>
                    <div class="divider"></div>
                    <div class="meta">
                        <div>{person_name}</div>
                        <div>{('<a href="https://' + website + '">' + website + '</a>') if website else ""}</div>
                    </div>
                </div>
            </div>
        </div>
        <!-- Generated: {now} -->
    </body>

</html>
""",
    )

    # Business card back
    write_text(
        files["business_card_back"],
        f"""<!doctype html>
<html lang="en">

    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{brand_name} - Business Card (Back)</title>
        <style>
            @page {{
                size: 3.5in 2in;
                margin: 0;
            }}

            :root {{
                --bg0: {css_vars["bg0"]};
                --bg1: {css_vars["bg1"]};
                --ink: {css_vars["ink"]};
                --muted: {css_vars["muted"]};
                --accent2: {css_vars["accent2"]};
            }}

            * {{ box-sizing: border-box; }}

            body {{
                margin: 0;
                width: 3.5in;
                height: 2in;
                font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                color: var(--ink);
                overflow: hidden;
            }}

            .card {{
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, var(--bg0), var(--bg1));
                position: relative;
            }}

            .card::before {{
                content: "";
                position: absolute;
                inset: 0;
                background:
                    radial-gradient(520px 240px at 20% 30%, {css_vars["accent2_12"]}, transparent 60%),
                    radial-gradient(420px 240px at 86% 16%, {css_vars["ink_10"]}, transparent 65%);
                pointer-events: none;
                opacity: 0.85;
            }}

            .safe {{
                position: relative;
                z-index: 1;
                width: 100%;
                height: 100%;
                padding: 0.24in;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }}

            .title {{
                font-size: 9pt;
                font-weight: 850;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: var(--accent2);
            }}

            .grid {{
                display: grid;
                grid-template-columns: 1fr;
                gap: 8px;
                margin-top: 10px;
            }}

            .row {{
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                gap: 10px;
                padding-bottom: 6px;
                border-bottom: 1px solid {css_vars["ink_10"]};
            }}

            .k {{
                font-size: 7.5pt;
                color: var(--muted);
                font-weight: 650;
            }}

            .v {{
                font-size: 8pt;
                font-weight: 750;
                color: var(--ink);
                text-align: right;
            }}

            .v a {{
                color: inherit;
                text-decoration: none;
            }}

            .footer {{
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                font-size: 7pt;
                color: var(--muted);
                font-weight: 650;
            }}
        </style>
    </head>

    <body>
        <div class="card" role="img" aria-label="{brand_name} business card back">
            <div class="safe">
                <div>
                    <div class="title">{person_title}</div>
                    <div class="grid" aria-label="Contact details">
                        <div class="row"><div class="k">Email</div><div class="v"><a href="mailto:{email}">{email}</a></div></div>
                        <div class="row"><div class="k">Phone</div><div class="v"><a href="tel:{phone}">{phone}</a></div></div>
                        {f'<div class="row"><div class="k">Website</div><div class="v"><a href="https://{website}">{website}</a></div></div>' if website else ''}
                        <div class="row"><div class="k">Location</div><div class="v">{location}</div></div>
                    </div>
                </div>

                <div class="footer">
                    <div>{brand_name}</div>
                    <div>{address}</div>
                </div>
            </div>
        </div>
        <!-- Generated: {now} -->
    </body>

</html>
""",
    )

    # Letterhead (A4)
    write_text(
        files["letterhead"],
        f"""<!doctype html>
<html lang="en">

    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{brand_name} - Letterhead</title>
        <style>
            @page {{
                size: A4;
                margin: 0;
            }}

            :root {{
                --bg0: {css_vars["bg0"]};
                --bg1: {css_vars["bg1"]};
                --ink: {css_vars["ink"]};
                --muted: {css_vars["muted"]};
                --accent2: {css_vars["accent2"]};
            }}

            * {{ box-sizing: border-box; }}

            body {{
                margin: 0;
                width: 210mm;
                height: 297mm;
                font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                color: var(--ink);
                background: #ffffff;
            }}

            .page {{
                width: 100%;
                height: 100%;
                position: relative;
            }}

            .header {{
                background: linear-gradient(135deg, var(--bg0), var(--bg1));
                padding: 18mm 22mm;
                border-bottom: 4px solid var(--accent2);
                position: relative;
                overflow: hidden;
            }}

            .header::before {{
                content: "";
                position: absolute;
                inset: 0;
                background-image: radial-gradient({css_vars["accent2_10"]} 1.5px, transparent 1.5px);
                background-size: 8mm 8mm;
                opacity: 0.6;
                pointer-events: none;
            }}

            .headerInner {{
                position: relative;
                z-index: 1;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12mm;
            }}

            .lockup {{
                display: flex;
                align-items: center;
                gap: 10mm;
            }}

            .logo {{
                width: 34mm;
                height: auto;
                display: block;
                filter: drop-shadow(0 8px 18px rgba(0, 0, 0, 0.12));
            }}

            .brandName {{
                font-size: 26pt;
                font-weight: 900;
                letter-spacing: -0.03em;
                line-height: 1;
            }}

            .tagline {{
                margin-top: 2mm;
                font-size: 11pt;
                font-weight: 650;
                color: var(--muted);
            }}

            .badges {{
                display: flex;
                flex-direction: column;
                gap: 3mm;
                align-items: flex-end;
            }}

            .badge {{
                background: {css_vars["accent2_12"]};
                border: 2px solid {css_vars["accent2_28"]};
                padding: 2mm 5mm;
                border-radius: 999px;
                font-size: 9pt;
                font-weight: 750;
                color: var(--accent2);
                white-space: nowrap;
            }}

            .content {{
                padding: 20mm 22mm;
                min-height: 200mm;
            }}

            .placeholder {{
                margin-top: 10mm;
                border: 2px dashed {css_vars["ink_14"]};
                border-radius: 14px;
                padding: 16px;
                color: var(--muted);
                font-weight: 650;
            }}

            .footer {{
                position: absolute;
                left: 0;
                right: 0;
                bottom: 0;
                padding: 10mm 22mm;
                border-top: 1px solid {css_vars["ink_12"]};
                background: linear-gradient(135deg, var(--bg0), var(--bg1));
            }}

            .footerGrid {{
                display: grid;
                grid-template-columns: 1.2fr 1fr 1fr;
                gap: 10mm;
                font-size: 9pt;
                color: var(--muted);
            }}

            .footerTitle {{
                font-weight: 850;
                color: var(--accent2);
                letter-spacing: 0.06em;
                text-transform: uppercase;
                margin-bottom: 2mm;
                font-size: 8.5pt;
            }}

            .footerGrid a {{
                color: inherit;
                text-decoration: none;
            }}
        </style>
    </head>

    <body>
        <div class="page">
            <div class="header">
                <div class="headerInner">
                    <div class="lockup">
                        {"<img class=\"logo\" src=\"" + logo_url + "\" alt=\"" + brand_name + " logo\">" if logo_url else ""}
                        <div>
                            <div class="brandName">{brand_name}</div>
                            {"<div class=\"tagline\">" + tagline + "</div>" if tagline else ""}
                        </div>
                    </div>
                    <div class="badges" aria-label="Brand badges">
                        {''.join([f'<div class="badge">{b}</div>' for b in badges])}
                    </div>
                </div>
            </div>

            <div class="content">
                <div class="placeholder">Your letter content goes here…</div>
            </div>

            <div class="footer">
                <div class="footerGrid">
                    <div>
                        <div class="footerTitle">Contact</div>
                        <div>{person_name}</div>
                        <div>{person_title}</div>
                    </div>
                    <div>
                        <div class="footerTitle">Reach</div>
                        <div><a href="mailto:{email}">{email}</a></div>
                        <div><a href="tel:{phone}">{phone}</a></div>
                        {f'<div><a href="https://{website}">{website}</a></div>' if website else ''}
                    </div>
                    <div>
                        <div class="footerTitle">Location</div>
                        <div>{location}</div>
                        <div>{address}</div>
                    </div>
                </div>
            </div>
        </div>
        <!-- Generated: {now} -->
    </body>

</html>
""",
    )

    # Email signature (HTML table for compatibility)
    write_text(
        files["email_signature"],
        f"""<!doctype html>
<html lang="en">

    <head>
        <meta charset="utf-8">
        <title>{brand_name} - Email Signature</title>
    </head>

    <body style="margin:0; padding:0; font-family:system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;">
        <table cellpadding="0" cellspacing="0" border="0"
            style="max-width:520px; border:1px solid rgba(0,0,0,.06); border-radius:14px; overflow:hidden; background:#ffffff;">
            <tr>
                <td colspan="2"
                    style="background: linear-gradient(135deg, {css_vars["bg0"]} 0%, {css_vars["bg1"]} 100%); padding:16px 18px; border-bottom: 3px solid {css_vars["accent2"]};">
                    <table cellpadding="0" cellspacing="0" border="0" width="100%">
                        <tr>
                            <td style="vertical-align:middle;">
                                <table cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td style="padding-right: 12px; vertical-align: middle;">
                                            {f'<img src="{logo_url}" alt="{brand_name} logo" width="46" style="display:block; width:46px; height:auto;" />' if logo_url else ''}
                                        </td>
                                        <td style="vertical-align: middle;">
                                            <div style="font-size: 20px; font-weight: 900; color: {css_vars["ink"]}; line-height:1.1;">
                                                {brand_name}</div>
                                            {f'<div style="font-size: 11px; color: {css_vars["muted"]}; font-weight: 650; margin-top:4px;">{tagline}</div>' if tagline else ''}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>

            <tr>
                <td colspan="2" style="padding: 16px 18px;">
                    <div style="font-size: 14px; font-weight: 850; color: {css_vars["ink"]};">{person_name}</div>
                    <div style="font-size: 12px; font-weight: 650; color: {css_vars["accent2"]}; margin-top:2px;">{person_title}</div>

                    <div style="margin-top: 10px; font-size: 11px; color: {css_vars["muted"]}; line-height: 1.7;">
                        <div><span style="font-weight:800; color:{css_vars["accent2"]};">Email:</span>
                            <a href="mailto:{email}" style="color:{css_vars["muted"]}; text-decoration:none;">{email}</a>
                        </div>
                        <div><span style="font-weight:800; color:{css_vars["accent2"]};">Phone:</span>
                            <a href="tel:{phone}" style="color:{css_vars["muted"]}; text-decoration:none;">{phone}</a>
                        </div>
                        {f'<div><span style="font-weight:800; color:{css_vars["accent2"]};">Web:</span> <a href="https://{website}" style="color:{css_vars["muted"]}; text-decoration:none;">{website}</a></div>' if website else ''}
                        <div><span style="font-weight:800; color:{css_vars["accent2"]};">Location:</span> {location}</div>
                    </div>
                </td>
            </tr>

            <tr>
                <td colspan="2" style="background: rgba(0,0,0,.02); padding: 12px 18px; border-top: 1px solid rgba(0,0,0,.06);">
                    <table cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            {''.join([f'<td style="padding-right: 8px;"><span style="background:{css_vars["accent2"]}; color:white; padding:4px 10px; border-radius:999px; font-size:8px; font-weight:850; display:inline-block; letter-spacing:.05em; text-transform:uppercase;">{b}</span></td>' for b in badges])}
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        <!-- Generated: {now} -->
    </body>

</html>
""",
    )

    # Brand sheet (simple one-page overview)
    write_text(
        files["brand_sheet"],
        f"""<!doctype html>
<html lang="en">

    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{brand_name} - Brand Sheet</title>
        <style>
            :root {{
                --bg0: {css_vars["bg0"]};
                --bg1: {css_vars["bg1"]};
                --ink: {css_vars["ink"]};
                --muted: {css_vars["muted"]};
                --accent: {css_vars["accent"]};
                --accent2: {css_vars["accent2"]};
            }}

            * {{ box-sizing: border-box; }}

            body {{
                margin: 0;
                font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                color: var(--ink);
                background: linear-gradient(135deg, var(--bg0), var(--bg1));
                padding: 28px 18px 48px;
            }}

            .wrap {{
                max-width: 980px;
                margin: 0 auto;
            }}

            .hero {{
                border-radius: 18px;
                border: 1px solid rgba(0,0,0,.06);
                background: rgba(255,255,255,.82);
                box-shadow: 0 18px 50px rgba(0,0,0,.08);
                overflow: hidden;
            }}

            .heroTop {{
                padding: 22px 22px;
                background: linear-gradient(135deg, var(--bg0), var(--bg1));
                border-bottom: 3px solid var(--accent2);
                display: flex;
                gap: 18px;
                align-items: center;
                justify-content: space-between;
            }}

            .lockup {{
                display: flex;
                align-items: center;
                gap: 14px;
            }}

            .logo {{
                width: 76px;
                height: auto;
                filter: drop-shadow(0 10px 18px rgba(0,0,0,.12));
            }}

            h1 {{
                margin: 0;
                font-size: 30px;
                letter-spacing: -0.03em;
                line-height: 1.05;
            }}

            .tagline {{
                margin-top: 6px;
                color: var(--muted);
                font-weight: 650;
            }}

            .grid {{
                display: grid;
                grid-template-columns: 1.4fr 1fr;
                gap: 16px;
                padding: 18px 22px 22px;
            }}

            .card {{
                border: 1px solid rgba(0,0,0,.06);
                border-radius: 16px;
                background: #fff;
                padding: 16px;
            }}

            .title {{
                font-size: 12px;
                letter-spacing: .08em;
                text-transform: uppercase;
                font-weight: 900;
                color: var(--accent2);
                margin-bottom: 10px;
            }}

            .badges {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }}

            .badge {{
                padding: 6px 10px;
                border-radius: 999px;
                background: {css_vars["accent2_10"]};
                border: 1px solid {css_vars["accent2_28"]};
                font-weight: 750;
                color: var(--accent2);
                font-size: 12px;
            }}

            .colors {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
            }}

            .swatch {{
                border-radius: 14px;
                border: 1px solid rgba(0,0,0,.08);
                padding: 10px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
            }}

            .dot {{
                width: 28px;
                height: 28px;
                border-radius: 10px;
                border: 1px solid rgba(0,0,0,.1);
            }}

            .swatch code {{
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
                font-size: 12px;
                color: var(--muted);
            }}

            @media (max-width: 840px) {{
                .grid {{
                    grid-template-columns: 1fr;
                }}
                .heroTop {{
                    flex-direction: column;
                    align-items: flex-start;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="wrap">
            <div class="hero">
                <div class="heroTop">
                    <div class="lockup">
                        {f'<img class="logo" src="{logo_url}" alt="{brand_name} logo">' if logo_url else ''}
                        <div>
                            <h1>{brand_name}</h1>
                            {f'<div class="tagline">{tagline}</div>' if tagline else ''}
                        </div>
                    </div>
                    <div style="color:var(--muted); font-weight:650;">
                        {f'<span>{website}</span>' if website else ''}
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <div class="title">Brand Pillars</div>
                        <div class="badges">
                            {''.join([f'<div class="badge">{b}</div>' for b in badges])}
                        </div>
                        <div style="margin-top:12px; color:var(--muted); font-weight:650; line-height:1.6;">
                            Use these pillars consistently across copy, design, and packaging. Keep spacing generous,
                            align to a grid, and prefer calm, premium contrast.
                        </div>
                    </div>
                    <div class="card">
                        <div class="title">Color Tokens</div>
                        <div class="colors">
                            <div class="swatch">
                                <div><div style="font-weight:800;">Accent</div><code>{css_vars["accent"]}</code></div>
                                <div class="dot" style="background:{css_vars["accent"]};"></div>
                            </div>
                            <div class="swatch">
                                <div><div style="font-weight:800;">Accent 2</div><code>{css_vars["accent2"]}</code></div>
                                <div class="dot" style="background:{css_vars["accent2"]};"></div>
                            </div>
                            <div class="swatch">
                                <div><div style="font-weight:800;">Ink</div><code>{css_vars["ink"]}</code></div>
                                <div class="dot" style="background:{css_vars["ink"]};"></div>
                            </div>
                            <div class="swatch">
                                <div><div style="font-weight:800;">Background</div><code>{css_vars["bg0"]}</code></div>
                                <div class="dot" style="background:{css_vars["bg0"]};"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <!-- Generated: {now} -->
    </body>

</html>
""",
    )

    base_url = f"/static/generated/{_sanitize_id(brand_id)}/collateral"

    # Index
    write_text(
        files["index"],
        f"""<!doctype html>
<html lang="en">

    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{brand_name} - Collateral Pack</title>
        <style>
            :root {{
                --bg0: {css_vars["bg0"]};
                --bg1: {css_vars["bg1"]};
                --ink: {css_vars["ink"]};
                --muted: {css_vars["muted"]};
                --accent2: {css_vars["accent2"]};
            }}

            * {{ box-sizing: border-box; }}

            body {{
                margin: 0;
                font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                color: var(--ink);
                background: linear-gradient(135deg, var(--bg0), var(--bg1));
                padding: 28px 18px 48px;
            }}

            .wrap {{
                max-width: 1240px;
                margin: 0 auto;
            }}

            .hero {{
                background: rgba(255,255,255,.86);
                border: 1px solid rgba(0,0,0,.06);
                border-radius: 18px;
                padding: 18px 18px;
                box-shadow: 0 18px 50px rgba(0,0,0,.08);
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
            }}

            .lockup {{
                display: flex;
                align-items: center;
                gap: 14px;
            }}

            .logo {{
                width: 56px;
                height: auto;
                filter: drop-shadow(0 10px 18px rgba(0,0,0,.12));
            }}

            h1 {{
                margin: 0;
                font-size: 20px;
                letter-spacing: -0.02em;
            }}

            .sub {{
                margin-top: 3px;
                color: var(--muted);
                font-weight: 650;
                font-size: 13px;
            }}

            .btnRow {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                justify-content: flex-end;
            }}

            .btn {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 10px 12px;
                border-radius: 12px;
                border: 1px solid rgba(0,0,0,.08);
                background: #ffffff;
                color: var(--ink);
                text-decoration: none;
                font-weight: 750;
            }}

            .btnPrimary {{
                background: var(--accent2);
                color: #ffffff;
                border-color: {css_vars["accent2_28"]};
            }}

            .grid {{
                margin-top: 16px;
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
            }}

            .card {{
                background: rgba(255,255,255,.9);
                border: 1px solid rgba(0,0,0,.06);
                border-radius: 18px;
                overflow: hidden;
                box-shadow: 0 12px 32px rgba(0,0,0,.06);
            }}

            .cardHead {{
                padding: 12px 14px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                border-bottom: 1px solid rgba(0,0,0,.06);
            }}

            .cardTitle {{
                font-weight: 850;
                letter-spacing: -0.01em;
            }}

            .cardMeta {{
                color: var(--muted);
                font-weight: 650;
                font-size: 12px;
            }}

            iframe {{
                width: 100%;
                border: 0;
                display: block;
                background: #fff;
            }}

            @media (max-width: 980px) {{
                .grid {{
                    grid-template-columns: 1fr;
                }}
                .btnRow {{
                    justify-content: flex-start;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="wrap">
            <div class="hero">
                <div class="lockup">
                    {f'<img class="logo" src="{logo_url}" alt="{brand_name} logo">' if logo_url else ''}
                    <div>
                        <h1>{brand_name} • Collateral Pack</h1>
                        <div class="sub">Generated {now}. Deterministic templates driven by brand config.</div>
                    </div>
                </div>
                <div class="btnRow">
                    <a class="btn btnPrimary" href="{base_url}/{files["brand_sheet"]}" target="_blank" rel="noreferrer">Open brand sheet</a>
                    <a class="btn" href="{base_url}/{files["letterhead"]}" target="_blank" rel="noreferrer">Open letterhead</a>
                </div>
            </div>

            <div class="grid">
                <div class="card">
                    <div class="cardHead">
                        <div>
                            <div class="cardTitle">Business card (front)</div>
                            <div class="cardMeta">3.5×2 in • Print-ready HTML</div>
                        </div>
                        <a class="btn" href="{base_url}/{files["business_card_front"]}" download>Download</a>
                    </div>
                    <iframe title="Business card front preview" src="{base_url}/{files["business_card_front"]}"></iframe>
                </div>
                <div class="card">
                    <div class="cardHead">
                        <div>
                            <div class="cardTitle">Business card (back)</div>
                            <div class="cardMeta">3.5×2 in • Print-ready HTML</div>
                        </div>
                        <a class="btn" href="{base_url}/{files["business_card_back"]}" download>Download</a>
                    </div>
                    <iframe title="Business card back preview" src="{base_url}/{files["business_card_back"]}"></iframe>
                </div>
                <div class="card">
                    <div class="cardHead">
                        <div>
                            <div class="cardTitle">Letterhead</div>
                            <div class="cardMeta">A4 • Print-ready HTML</div>
                        </div>
                        <a class="btn" href="{base_url}/{files["letterhead"]}" download>Download</a>
                    </div>
                    <iframe title="Letterhead preview" style="height:740px;" src="{base_url}/{files["letterhead"]}"></iframe>
                </div>
                <div class="card">
                    <div class="cardHead">
                        <div>
                            <div class="cardTitle">Email signature</div>
                            <div class="cardMeta">Copy/paste into email clients</div>
                        </div>
                        <a class="btn" href="{base_url}/{files["email_signature"]}" download>Download</a>
                    </div>
                    <iframe title="Email signature preview" style="height:420px;" src="{base_url}/{files["email_signature"]}"></iframe>
                </div>
                <div class="card">
                    <div class="cardHead">
                        <div>
                            <div class="cardTitle">Brand sheet</div>
                            <div class="cardMeta">Web preview • Uses brand tokens</div>
                        </div>
                        <a class="btn" href="{base_url}/{files["brand_sheet"]}" download>Download</a>
                    </div>
                    <iframe title="Brand sheet preview" style="height:620px;" src="{base_url}/{files["brand_sheet"]}"></iframe>
                </div>
            </div>
        </div>
        <!-- Generated: {now} -->
    </body>

</html>
""",
    )

    manifest = {
        "generatedAt": now,
        "brand": {"id": brand.get("id"), "name": brand_name},
        "baseUrl": base_url,
        "files": {k: f"{base_url}/{v}" for k, v in files.items() if v.endswith(".html")},
        "source": "memory-router collateral_pack generator",
    }
    write_text(files["manifest"], json.dumps(manifest, indent=2))

    return {k: f"{base_url}/{v}" for k, v in files.items() if v.endswith(".html")}
