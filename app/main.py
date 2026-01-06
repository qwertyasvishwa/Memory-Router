import io
import os
import logging
import datetime
from typing import List, Optional
from urllib.parse import quote

import json

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile, File, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ledger import ledger_service
from .schemas import (
    ArtifactType,
    EntryCategory,
    EntryCreate,
    EntryNormalized,
    LedgerEntryCreate,
    LedgerEntryNormalized,
    TodoEntryCreate,
    TodoEntryNormalized,
    ValueTag,
    build_ledger_entry,
    build_normalized_entry,
)
from .sharepoint_client import graph_client
from .todos import todo_service
from .git_sync import GitError, conflict_files, conflict_markers_preview, fetch, get_status, pull_rebase, push
from .brands import BrandSpec, list_brands
from .brand_guidelines_samples import (
    list_brand_guidelines_samples,
    load_brand_guidelines_sample,
    resolve_static_paths,
)
from .collateral_pack import generate_collateral_pack
from .tools_registry import ToolCreate, ToolRunRequest, ToolRunResult, ToolSpec, tool_registry
from .tool_store import load_tools, save_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("memory_router")

QUICK_LINKS = [
    {
        "label": "Memory Router folder",
        "url": "https://vishwaraj04.sharepoint.com/sites/Vishwa/Shared%20Documents/Memory%20Router",
    },
    {
        "label": "Drive (Vishwa)",
        "url": "https://vishwaraj04.sharepoint.com/sites/Vishwa/Shared%20Documents",
    },
]

HAPPY_EATS_STORY = """Once Upon a Time in the Lush Countryside of India...

In the heart of a vibrant village surrounded by the verdant splendor of nature, the essence of traditional Indian cuisine thrived. Here, the secret recipes passed down through generations whispered the tales of taste, health, and harmony with nature. From the sun-kissed fields to the bustling kitchen corners, every grain, every spice held a story—a story of the land, a story of life.

This is where "Happy Eats" was born.

The logo of Happy Eats, with its heart cradled by nurturing leaves, is an emblem of love—a love for food that is as pure as a grandmother's hug, as authentic as the earth itself. The heart represents the care we put into selecting the finest organic ingredients, the passion that simmers in our cooking, and the joy that comes from eating well and healthy.

The leaves, verdant and fresh, are a testament to our commitment to freshness. Just like the leaves that protect and nourish the heart of the plant, our sustainable packaging protects the integrity and flavor of our food, ensuring that every bite you take is a whisper of the pure, untainted earth.

Every curve of the letters in Happy Eats echoes the laughter and conversations that encircle Indian dining tables. They embody the seamless blend of old-world charm and contemporary needs, bringing forth a sense of nostalgia in every crunch of our banana chips, every bite of our multilayered khakhra, and the homely warmth of our thepla.

As you savor the flavors of Happy Eats, you're not just enjoying a snack; you're partaking in a legacy. You're at the crossroads of past and present, where every flavor tells a story, and every meal is a celebration of life's simple pleasures.

So, with every pack of Happy Eats you open, let the aroma transport you to the serene fields, the bustling markets, and the loving kitchens of India. Unwrap a story, take a bite, and let the timeless taste of nostalgia fill your soul with happiness.

...And thus, "Happy Eats" isn't just a brand; it's a journey—a journey of taste that transcends time, bringing the treasures of the past to the table of the present."""

HAPPY_EATS_BRAND_PILLARS = [
    {
        "title": "100% Handmade with Love",
        "icon": "🤲",
        "description": "Every product is crafted by hand, preserving traditional recipes and techniques passed down through generations.",
        "details": "Our artisans bring decades of expertise, ensuring each bite carries the authentic taste of home kitchens."
    },
    {
        "title": "Organic & Pure Ingredients",
        "icon": "🌿",
        "description": "No maida, no artificial preservatives, no trans fats. Just honest, clean ingredients from trusted farms.",
        "details": "We source directly from organic farmers who practice sustainable agriculture, ensuring purity from farm to fork."
    },
    {
        "title": "Freshness Locked In",
        "icon": "✨",
        "description": "Roasted and packed fresh to preserve natural aroma, crunch, and nutrition in every pack.",
        "details": "Our innovative packaging protects flavor integrity while being environmentally conscious."
    },
    {
        "title": "Cholesterol-Free & Heart-Healthy",
        "icon": "❤️",
        "description": "Zero cholesterol, zero trans fat. Snacking that loves your heart back.",
        "details": "Guilt-free indulgence for health-conscious families who refuse to compromise on taste."
    },
    {
        "title": "Ready to Eat Convenience",
        "icon": "🍽️",
        "description": "Perfect for busy lifestyles—open, savor, enjoy. No cooking, no mess, just pure delight.",
        "details": "Ideal for travel, office snacks, tea-time, or unexpected guests. Always ready when you need them."
    },
    {
        "title": "Rooted in Heritage",
        "icon": "🏛️",
        "description": "Recipes inspired by India's rich culinary traditions, adapted for modern wellness.",
        "details": "Each flavor tells a regional story—from Gujarat's khakhra to South India's dosa varieties."
    },
    {
        "title": "Sustainable Packaging",
        "icon": "♻️",
        "description": "Hard paper packaging that protects our products and our planet.",
        "details": "Eco-friendly materials that reduce environmental impact without compromising product quality."
    },
    {
        "title": "Flavor Diversity",
        "icon": "🎨",
        "description": "From classic to adventurous—over 60 flavors across our product range.",
        "details": "Something for every palate: traditional favorites, regional specialties, and innovative fusions."
    },
    {
        "title": "Family Wellness",
        "icon": "👨‍👩‍👧‍👦",
        "description": "Snacks that bring families together, with nutrition parents trust and taste kids love.",
        "details": "Perfect for all ages—from toddlers to grandparents, everyone finds their favorite."
    },
    {
        "title": "Certified Quality",
        "icon": "✅",
        "description": "FSSAI certified, rigorously tested, consistently excellent.",
        "details": "Every batch meets stringent quality standards, ensuring safety and consistency."
    }
]

HAPPY_EATS_PRODUCTS = [
    {
        "name": "Khakhra",
        "packaging": "Hard paper packaging",
        "variants": [
            {"flavor": "Methi (Fenugreek)", "color": "#4f8b2c", "badge_color": "#3d6e23"},
            {"flavor": "Chatpata (Tangy)", "color": "#6e4ac8", "badge_color": "#5638a0"},
            {"flavor": "Masala (Spicy)", "color": "#d76c2f", "badge_color": "#b05624"},
            {"flavor": "Jeera (Cumin)", "color": "#6b5244", "badge_color": "#544034"},
            {"flavor": "Farali (Fasting)", "color": "#e87d3e", "badge_color": "#c66830"},
        ],
        "total_flavors": "28 authentic flavors",
        "description": "Thin, crispy, roasted wheat crackers—Gujarat's pride, India's favorite."
    },
    {
        "name": "Banana Chips",
        "packaging": "Hard paper packaging",
        "variants": [
            {"flavor": "Classic Salted", "color": "#f4a261", "badge_color": "#e07a3c"},
            {"flavor": "Kerala Style", "color": "#8b4f2c", "badge_color": "#6e3e23"}
        ],
        "total_flavors": "2 timeless flavors",
        "description": "Crispy, golden slices of pure Kerala nostalgia."
    },
    {
        "name": "Thepla",
        "packaging": "Hard paper packaging",
        "variants": [
            {"flavor": "Classic Methi", "color": "#4f8b2c", "badge_color": "#3d6e23"},
            {"flavor": "Spiced Masala", "color": "#d76c2f", "badge_color": "#b05624"}
        ],
        "total_flavors": "2 comforting flavors",
        "description": "Soft, flavorful flatbreads—perfect for travel or tiffin."
    },
    {
        "name": "Dosa Khakhra",
        "packaging": "Hard packaging",
        "variants": [],
        "total_flavors": "20 South-Indian inspired flavors",
        "description": "The crunch of khakhra meets the soul of dosa—innovation at its finest."
    },
    {
        "name": "Roasted Wheat Maththi",
        "packaging": "Hard box outside / Plastic inside",
        "variants": [],
        "total_flavors": "14 gourmet flavors (7 classic + 7 premium)",
        "description": "Flaky, buttery, melt-in-mouth delights for festive celebrations."
    },
    {
        "name": "Chakri",
        "packaging": "Hard box outside / Plastic inside",
        "variants": [
            {"flavor": "Traditional Spice", "color": "#d76c2f", "badge_color": "#b05624"},
            {"flavor": "Festive Mix", "color": "#6e4ac8", "badge_color": "#5638a0"}
        ],
        "total_flavors": "2 festive flavors",
        "description": "Spiral-shaped crunchy wonders that define Diwali snacking."
    },
    {
        "name": "Peanut Mawa Malai Chikki",
        "packaging": "Hard box outside / Plastic inside",
        "variants": [
            {"flavor": "Rich Mawa Malai", "color": "#8b6f47", "badge_color": "#6e5638"}
        ],
        "total_flavors": "1 indulgent flavor",
        "description": "Crunchy peanuts meet creamy mawa—a sweet symphony of textures."
    }
]

BRAND_ASSETS = [
    {
        "category": "Packaging Designs",
        "items": [
            {"name": "Khakhra - Methi", "file": "khakhra_methi.jpg", "type": "Product Packaging"},
            {"name": "Khakhra - Chatpata", "file": "khakhra_chatpata.jpg", "type": "Product Packaging"},
            {"name": "Khakhra - Masala", "file": "khakhra_masala.jpg", "type": "Product Packaging"},
            {"name": "Khakhra - Jeera", "file": "khakhra_jeera.jpg", "type": "Product Packaging"},
            {"name": "Khakhra - Farali", "file": "khakhra_farali.jpg", "type": "Product Packaging"},
        ]
    },
    {
        "category": "Logo & Brand Identity",
        "items": [
            {"name": "Happy Eats Logo - Primary", "file": "logo_primary.svg", "type": "Vector Logo"},
            {"name": "Happy Eats Logo - White", "file": "logo_white.svg", "type": "Vector Logo"},
            {"name": "Happy Eats Logo - Icon Only", "file": "logo_icon.svg", "type": "Icon"},
            {"name": "Leaf Heart Symbol", "file": "symbol_leaf_heart.svg", "type": "Brand Mark"},
            {"name": "100% Handmade Badge", "file": "badge_handmade.svg", "type": "Quality Seal"},
        ]
    },
    {
        "category": "Collateral - Business Stationery",
        "items": [
            {"name": "Business Card - Front", "file": "/static/happy-eats/collateral/business-card-front.html", "type": "HTML (Print Ready)"},
            {"name": "Business Card - Back", "file": "/static/happy-eats/collateral/business-card-back.html", "type": "HTML (Print Ready)"},
            {"name": "Letterhead", "file": "/static/happy-eats/collateral/letterhead.html", "type": "HTML (Print Ready)"},
            {"name": "Email Signature", "file": "/static/happy-eats/collateral/email-signature.html", "type": "HTML Template"},
        ]
    },
    {
        "category": "Collateral - Marketing",
        "items": [
            {"name": "Brochure - Tri-fold", "file": "/static/happy-eats/collateral/brochure.html", "type": "HTML (Print Ready)"},
            {"name": "Social Media Post Template", "file": "/static/happy-eats/collateral/social-media-post.html", "type": "HTML (1080x1080)"},
            {"name": "Collateral Guide", "file": "/static/happy-eats/collateral/README.md", "type": "Documentation"},
        ]
    },
    {
        "category": "Collateral - Retail & POS",
        "items": [
            {"name": "Shelf Talker", "file": "shelf_talker.pdf", "type": "Print Ready"},
            {"name": "Danglers", "file": "danglers.pdf", "type": "Print Ready"},
            {"name": "Standee", "file": "standee.pdf", "type": "Print Ready"},
            {"name": "Window Decal", "file": "window_decal.pdf", "type": "Print Ready"},
            {"name": "Price Tags", "file": "price_tags.pdf", "type": "Print Ready"},
        ]
    },
    {
        "category": "Icons & Badges",
        "items": [
            {"name": "No Maida Icon", "file": "icon_no_maida.svg", "type": "SVG Icon"},
            {"name": "Ready to Eat Icon", "file": "icon_ready_to_eat.svg", "type": "SVG Icon"},
            {"name": "Cholesterol Free Icon", "file": "icon_cholesterol_free.svg", "type": "SVG Icon"},
            {"name": "Zero Trans Fat Icon", "file": "icon_zero_trans_fat.svg", "type": "SVG Icon"},
            {"name": "100% Wheat Flour Badge", "file": "badge_wheat_flour.svg", "type": "SVG Badge"},
        ]
    }
]

def _parse_enum_list(raw: Optional[str], enum_cls):
    values: List = []
    if not raw:
        return values
    for part in raw.split(","):
        cleaned = part.strip().lstrip("#").split("/")[-1]
        if not cleaned:
            continue
        for enum_member in enum_cls:
            if cleaned.lower() == enum_member.value.lower():
                values.append(enum_member)
                break
    return values


async def _record_ledger_for_entry(
    entry: EntryNormalized,
    *,
    item_id: str,
    source: str,
) -> None:
    summary = entry.content_normalized[:240] or entry.content_raw[:240]
    artifact_tag = ArtifactType.NOTE if entry.category == EntryCategory.NOTE else ArtifactType.WORKFLOW_DECISION
    try:
        await ledger_service.log_entry(
            LedgerEntryCreate(
                title=f"{entry.category.value.title()} entry captured",
                summary=summary,
                theme="Workflow",
                lens="MemoryRouter",
                project=entry.project,
                value_tags=[ValueTag.GROWTH, ValueTag.EFFICIENCY],
                artifact_tags=[artifact_tag],
                references=[
                    f"https://graph.microsoft.com/v1.0/drives/{graph_client.settings.drive_id}/items/{item_id}"
                ],
            ),
            source=source,
            actor="memory-router",
        )
    except Exception as exc:
        logger.warning("Failed to log ledger entry for %s: %s", entry.id, exc)

app = FastAPI(title="Memory Router", version="0.1.0")

# Static assets (favicon, etc.)
app.mount("/static", StaticFiles(directory=os.path.join("app", "static")), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_redirect() -> RedirectResponse:
    # Many browsers request /favicon.ico by default.
    return RedirectResponse(url="/static/favicon.ico", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

templates = Jinja2Templates(directory="app/templates")


def _happy_eats_logo_path() -> str:
    return os.path.join("app", "static", "happy-eats", "brand", "logo.png")


def _happy_eats_logo_is_present() -> bool:
    try:
        return os.path.getsize(_happy_eats_logo_path()) > 0
    except OSError:
        return False

# Load locally persisted tools on startup (safe default). If the store is missing,
# we still have the seeded example tool.
load_tools()

# In-memory session view of accepted entries (not a database).
IN_MEMORY_ENTRIES: List[EntryNormalized] = []


def _repo_root() -> str:
    # This file lives in <repo>/app/main.py
    return str(__import__("pathlib").Path(__file__).resolve().parents[1])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    todos = todo_service.list_entries()
    ledger_entries = ledger_service.list_entries()[:5]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "quick_links": QUICK_LINKS,
            "todos": todos,
            "recent_ledger": ledger_entries,
        },
    )


@app.get("/happy-eats", response_class=HTMLResponse)
async def happy_eats_page(request: Request) -> HTMLResponse:
    """Happy Eats brand landing page"""
    return templates.TemplateResponse(
        "happy_eats.html",
        {
            "request": request,
            "products": HAPPY_EATS_PRODUCTS,
            "story": HAPPY_EATS_STORY,
        },
    )


@app.get("/happy-eats/brand-pillars", response_class=HTMLResponse)
async def happy_eats_brand_pillars(request: Request) -> HTMLResponse:
    """Happy Eats brand pillars detail page"""
    return templates.TemplateResponse(
        "happy_eats_pillars.html",
        {
            "request": request,
            "pillars": HAPPY_EATS_BRAND_PILLARS,
        },
    )


@app.get("/happy-eats/brand-assets", response_class=HTMLResponse)
async def happy_eats_brand_assets(request: Request) -> HTMLResponse:
    """Happy Eats brand assets library"""
    # Transform BRAND_ASSETS into the format expected by template
    asset_categories = [
        {
            "name": "Packaging Designs",
            "icon": "📦",
            "description": "Product packaging designs for all Happy Eats collections",
            "assets": [
                {"name": "Khakhra - Methi", "format": "JPG", "description": "Green variant packaging design with illustrated character", "download_url": "/static/happy-eats/packaging/khakhra_methi.jpg", "preview_url": "/static/happy-eats/packaging/khakhra_methi.jpg"},
                {"name": "Khakhra - Chatpata", "format": "JPG", "description": "Purple variant packaging design with illustrated character", "download_url": "/static/happy-eats/packaging/khakhra_chatpata.jpg", "preview_url": "/static/happy-eats/packaging/khakhra_chatpata.jpg"},
                {"name": "Khakhra - Masala", "format": "JPG", "description": "Orange variant packaging design with illustrated character", "download_url": "/static/happy-eats/packaging/khakhra_masala.jpg", "preview_url": "/static/happy-eats/packaging/khakhra_masala.jpg"},
                {"name": "Khakhra - Jeera", "format": "JPG", "description": "Brown variant packaging design with illustrated character", "download_url": "/static/happy-eats/packaging/khakhra_jeera.jpg", "preview_url": "/static/happy-eats/packaging/khakhra_jeera.jpg"},
                {"name": "Khakhra - Farali", "format": "JPG", "description": "Orange variant packaging design for fasting snacks", "download_url": "/static/happy-eats/packaging/khakhra_farali.jpg", "preview_url": "/static/happy-eats/packaging/khakhra_farali.jpg"},
            ]
        },
        {
            "name": "Business Stationery",
            "icon": "📄",
            "description": "Professional business cards, letterhead, and email signatures",
            "assets": [
                {"name": "Business Card - Front", "format": "HTML", "description": "Print-ready business card front (3.5\" × 2\") with brand colors and logo", "download_url": "/static/happy-eats/collateral/business-card-front.html", "preview_url": "/static/happy-eats/collateral/business-card-front.html"},
                {"name": "Business Card - Front (Enhanced)", "format": "HTML", "description": "Enhanced version with micro icons and improved layout", "download_url": "/static/happy-eats/collateral/business-card-front-v2.html", "preview_url": "/static/happy-eats/collateral/business-card-front-v2.html"},
                {"name": "Business Card - Back", "format": "HTML", "description": "Print-ready business card back with contact information", "download_url": "/static/happy-eats/collateral/business-card-back.html", "preview_url": "/static/happy-eats/collateral/business-card-back.html"},
                {"name": "Business Card - Back (Enhanced)", "format": "HTML", "description": "Enhanced version with better icon alignment and badges", "download_url": "/static/happy-eats/collateral/business-card-back-v2.html", "preview_url": "/static/happy-eats/collateral/business-card-back-v2.html"},
                {"name": "Letterhead", "format": "HTML", "description": "A4 letterhead template with brand header and footer", "download_url": "/static/happy-eats/collateral/letterhead.html", "preview_url": "/static/happy-eats/collateral/letterhead.html"},
                {"name": "Letterhead (Enhanced)", "format": "HTML", "description": "Enhanced version with packaging design elements and micro icons", "download_url": "/static/happy-eats/collateral/letterhead-v2.html", "preview_url": "/static/happy-eats/collateral/letterhead-v2.html"},
        {
            "name": "Marketing Collateral",
            "icon": "📢",
            "description": "Brochures, social media templates, and promotional materials",
            "assets": [
                {"name": "Collateral Gallery (All-in-one)", "format": "HTML", "description": "Gallery page to preview and download all collateral files", "download_url": "/static/happy-eats/collateral/index.html", "preview_url": "/static/happy-eats/collateral/index.html"},
                {"name": "Social Posts Gallery - 11 Posts", "format": "HTML", "description": "Complete gallery with 11 social media post templates across 5 categories", "download_url": "/static/happy-eats/collateral/social-posts/index.html", "preview_url": "/static/happy-eats/collateral/social-posts/index.html"},
                {"name": "New Year 2026 Post", "format": "HTML", "description": "Seasonal greeting with product packaging (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/new-year-2026.html", "preview_url": "/static/happy-eats/collateral/social-posts/new-year-2026.html"},
                {"name": "New Year 2026 Generator (5 Styles)", "format": "HTML", "description": "Interactive New Year post generator with 5 exportable styles (PNG download)", "download_url": "/static/happy-eats/collateral/social-posts/new-year-2026-variants.html", "preview_url": "/static/happy-eats/collateral/social-posts/new-year-2026-variants.html"},
                {"name": "Khakhra Methi Spotlight", "format": "HTML", "description": "Single product variant showcase (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/product-khakhra-methi.html", "preview_url": "/static/happy-eats/collateral/social-posts/product-khakhra-methi.html"},
                {"name": "Khakhra Collection", "format": "HTML", "description": "4-variant product collection grid (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/product-collection.html", "preview_url": "/static/happy-eats/collateral/social-posts/product-collection.html"},
                {"name": "Brand Values Post", "format": "HTML", "description": "4-pillar brand values showcase (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/brand-values.html", "preview_url": "/static/happy-eats/collateral/social-posts/brand-values.html"},
                {"name": "Taste the Tradition", "format": "HTML", "description": "Heritage & tradition messaging (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/taste-tradition.html", "preview_url": "/static/happy-eats/collateral/social-posts/taste-tradition.html"},
                {"name": "Behind the Scenes", "format": "HTML", "description": "3-step traditional process showcase (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/behind-the-scenes.html", "preview_url": "/static/happy-eats/collateral/social-posts/behind-the-scenes.html"},
                {"name": "Health Benefits", "format": "HTML", "description": "4 key health benefits showcase (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/health-benefits.html", "preview_url": "/static/happy-eats/collateral/social-posts/health-benefits.html"},
                {"name": "Recipe Ideas", "format": "HTML", "description": "5 ways to enjoy khakhra (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/recipe-ideas.html", "preview_url": "/static/happy-eats/collateral/social-posts/recipe-ideas.html"},
                {"name": "Customer Testimonial", "format": "HTML", "description": "5-star review showcase (1080×1080px)", "download_url": "/static/happy-eats/collateral/social-posts/testimonial.html", "preview_url": "/static/happy-eats/collateral/social-posts/testimonial.html"},
                {"name": "Tri-fold Brochure", "format": "HTML", "description": "A4 landscape tri-fold brochure with products and brand story", "download_url": "/static/happy-eats/collateral/brochure.html", "preview_url": "/static/happy-eats/collateral/brochure.html"},
                {"name": "Collateral Guide", "format": "MD", "description": "Complete guide on using and customizing brand collateral", "download_url": "/static/happy-eats/collateral/README.md", "preview_url": "/static/happy-eats/collateral/README.md"},
            ]
        },      {"name": "Tri-fold Brochure", "format": "HTML", "description": "A4 landscape tri-fold brochure with products and brand story", "download_url": "/static/happy-eats/collateral/brochure.html", "preview_url": "/static/happy-eats/collateral/brochure.html"},
                {"name": "Collateral Guide", "format": "MD", "description": "Complete guide on using and customizing brand collateral", "download_url": "/static/happy-eats/collateral/README.md", "preview_url": "/static/happy-eats/collateral/README.md"},
            ]
        },
        {
            "name": "Logo & Brand Identity",
            "icon": "🎨",
            "description": "Logo variations, brand marks, and identity guidelines",
            "assets": [
                {"name": "Primary Logo", "format": "PNG", "description": "Primary Happy Eats logo (provided)", "download_url": "/static/happy-eats/brand/logo.png", "preview_url": "/static/happy-eats/brand/logo.png"},
                {"name": "White Logo", "format": "SVG", "description": "White version for dark backgrounds (coming soon)", "download_url": "#", "preview_url": "#"},
                {"name": "Leaf Heart Symbol", "format": "SVG", "description": "Standalone brand mark (coming soon)", "download_url": "#", "preview_url": "#"},
            ]
        },
        {
            "name": "Quality Badges",
            "icon": "✨",
            "description": "Product quality seals and certification badges",
            "assets": [
                {"name": "100% Handmade", "format": "SVG", "description": "Quality badge for handmade products (coming soon)", "download_url": "#", "preview_url": "#"},
                {"name": "No Maida", "format": "SVG", "description": "Health badge for maida-free products (coming soon)", "download_url": "#", "preview_url": "#"},
                {"name": "Zero Trans Fat", "format": "SVG", "description": "Health badge for zero trans fat (coming soon)", "download_url": "#", "preview_url": "#"},
                {"name": "Cholesterol Free", "format": "SVG", "description": "Health badge for cholesterol-free products (coming soon)", "download_url": "#", "preview_url": "#"},
            ]
        }
    ]

    return templates.TemplateResponse(
        "happy_eats_assets.html",
        {
            "request": request,
            "asset_categories": asset_categories,
            "happy_eats_logo_present": _happy_eats_logo_is_present(),
        },
    )


@app.get("/happy-eats/brand-logo", response_class=HTMLResponse)
async def happy_eats_brand_logo(request: Request) -> HTMLResponse:
    """Upload/replace the Happy Eats logo used by collateral templates."""
    return templates.TemplateResponse(
        "happy_eats_logo_upload.html",
        {
            "request": request,
            "logo_present": _happy_eats_logo_is_present(),
            "logo_url": "/static/happy-eats/brand/logo.png",
        },
    )


@app.post("/happy-eats/brand-logo")
async def happy_eats_brand_logo_upload(file: UploadFile = File(...)) -> RedirectResponse:
    content_type = (file.content_type or "").lower()
    allowed = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content-type '{file.content_type}'. Upload PNG/JPEG/WEBP.",
        )

    # Read bytes (cap to 5MB)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload")
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 5MB)")

    # Ensure folder exists
    os.makedirs(os.path.dirname(_happy_eats_logo_path()), exist_ok=True)

    # Save as logo.png (even if the user uploads jpg/webp). This keeps URLs stable.
    with open(_happy_eats_logo_path(), "wb") as f:
        f.write(data)

    return RedirectResponse(url="/happy-eats/brand-logo", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/tools", response_class=HTMLResponse)
async def tools_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "tools.html",
        {
            "request": request,
            "tools": tool_registry.list_tools(),
            "brands": list_brands(),
            "run_result": None,
        },
    )


@app.post("/tools", response_class=HTMLResponse)
async def tools_upsert_form(
    request: Request,
    tool_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(default=""),
    kind: str = Form(default="builtin"),
    entrypoint: str | None = Form(default=None),
) -> RedirectResponse:
    payload = ToolCreate(
        id=tool_id,
        name=name,
        description=description or "",
        kind=kind,
        entrypoint=(entrypoint or None),
    )
    tool_registry.upsert(payload)
    save_tools()
    return RedirectResponse(url="/tools", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/tools/run", response_class=HTMLResponse)
async def tools_run_form(
    request: Request,
    tool_id: str = Form(...),
    input_json: str = Form(default=""),
) -> HTMLResponse:
    try:
        parsed = json.loads(input_json) if input_json.strip() else {}
        if not isinstance(parsed, dict):
            raise ValueError("Input JSON must be an object")
    except Exception as exc:
        parsed = {}
        run_result = {"ok": False, "tool_id": tool_id, "error": f"Invalid JSON: {exc}"}
        return templates.TemplateResponse(
            "tools.html",
            {"request": request, "tools": tool_registry.list_tools(), "brands": list_brands(), "run_result": run_result},
        )

    result = tool_registry.run(tool_id, ToolRunRequest(input=parsed))
    return templates.TemplateResponse(
        "tools.html",
        {"request": request, "tools": tool_registry.list_tools(), "brands": list_brands(), "run_result": result.model_dump()},
    )


@app.get("/tools/social-posts/new-year", response_class=HTMLResponse)
async def tools_new_year_generator(
    request: Request,
    brand: str | None = None,
    year: str | None = None,
) -> HTMLResponse:
    brands = list_brands()
    selected_brand = (brand or "").strip()
    if not selected_brand or not any(b.id == selected_brand for b in brands):
        selected_brand = brands[0].id if brands else "happy-eats"

    resolved_year = (year or "").strip() or str(datetime.date.today().year + 1)
    generator_src = (
        "/static/tools/social-posts/new-year/index.html"
        f"?brand={quote(selected_brand)}&year={quote(resolved_year)}"
    )

    return templates.TemplateResponse(
        "tools_new_year.html",
        {
            "request": request,
            "brands": brands or [BrandSpec(id="happy-eats", name="Happy Eats")],
            "selected_brand": selected_brand,
            "year": resolved_year,
            "generator_src": generator_src,
        },
    )


@app.get("/tools/collaterals", response_class=HTMLResponse)
async def tools_collaterals_view(
    request: Request,
    brand: str | None = None,
) -> HTMLResponse:
    brands = list_brands()
    selected_brand = (brand or "").strip()
    if not selected_brand or not any(b.id == selected_brand for b in brands):
        selected_brand = brands[0].id if brands else "happy-eats"

    generated_index_url = f"/static/generated/{selected_brand}/collateral/index.html"
    # Only show preview link if the file exists on disk.
    generated_exists = os.path.exists(os.path.join("app", "static", "generated", selected_brand, "collateral", "index.html"))

    return templates.TemplateResponse(
        "tools_collaterals.html",
        {
            "request": request,
            "brands": brands or [BrandSpec(id="happy-eats", name="Happy Eats")],
            "selected_brand": selected_brand,
            "generated_index_url": generated_index_url if generated_exists else None,
        },
    )


@app.get("/tools/brand-guidelines", response_class=HTMLResponse)
async def tools_brand_guidelines_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "tools_brand_guidelines.html",
        {"request": request, "samples": list_brand_guidelines_samples()},
    )


@app.get("/tools/brand-guidelines/samples/{sample_id}", response_class=HTMLResponse)
async def tools_brand_guidelines_sample_view(request: Request, sample_id: str) -> HTMLResponse:
    try:
        sample = load_brand_guidelines_sample(sample_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load sample: {exc}",
        ) from exc

    sample = resolve_static_paths(sample)
    return templates.TemplateResponse(
        "tools_brand_guidelines_sample.html",
        {"request": request, "sample": sample},
    )


@app.post("/tools/collaterals/generate", response_class=RedirectResponse)
async def tools_collaterals_generate(
    brand: str = Form(...),
) -> RedirectResponse:
    brands = list_brands()
    selected_brand = (brand or "").strip()
    if not selected_brand or not any(b.id == selected_brand for b in brands):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown brand")

    urls = generate_collateral_pack(selected_brand)
    return RedirectResponse(url=urls["index"], status_code=status.HTTP_303_SEE_OTHER)


@app.get("/drive", response_class=HTMLResponse)
async def browse_drive(
    request: Request,
    path: Optional[str] = None,
    drive_id: Optional[str] = None,
) -> HTMLResponse:
    """
    Simple browser over drives accessible to the app registration.
    """
    selected_drive_id = drive_id or graph_client.settings.drive_id
    use_default_drive = selected_drive_id == graph_client.settings.drive_id and drive_id is None
    base_folder = None if use_default_drive else ""

    logger.info(
        "Drive browse requested drive=%s path=%s", selected_drive_id, path or "/"
    )
    try:
        items = await graph_client.list_children(
            path,
            drive_id=selected_drive_id,
            base_folder=base_folder,
        )
        drives = await graph_client.list_available_drives()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list drive items: {exc}",
        ) from exc

    # Normalize path for display / navigation
    normalized_path = (path or "").strip("/")
    segments = [seg for seg in normalized_path.split("/") if seg] if normalized_path else []

    return templates.TemplateResponse(
        "drive.html",
        {
            "request": request,
            "items": items,
            "path": normalized_path,
            "segments": segments,
            "selected_drive_id": selected_drive_id,
            "drives": drives,
        },
    )


@app.get("/ledger", response_class=HTMLResponse)
async def ledger_view(request: Request) -> HTMLResponse:
    entries = ledger_service.list_entries()
    return templates.TemplateResponse(
        "ledger.html",
        {
            "request": request,
            "entries": entries,
            "value_tags": list(ValueTag),
            "artifact_tags": list(ArtifactType),
        },
    )


@app.post("/todos", response_class=HTMLResponse)
async def create_todo(
    request: Request,
    title: str = Form(...),
    details: Optional[str] = Form(default=None),
    due_date: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
) -> RedirectResponse:
    payload = TodoEntryCreate(
        title=title,
        details=details or None,
        due_date=due_date or None,
        tags=[t.strip() for t in (tags or "").split(",") if t.strip()],
    )
    try:
        await todo_service.add_entry(payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to record todo: {exc}",
        ) from exc
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/ledger", response_class=HTMLResponse)
async def ledger_form_submit(
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    theme: str = Form(...),
    lens: str = Form(...),
    project: Optional[str] = Form(default=None),
    value_tags: Optional[str] = Form(default=None),
    artifact_tags: Optional[str] = Form(default=None),
    references: Optional[str] = Form(default=None),
) -> RedirectResponse:
    payload = LedgerEntryCreate(
        title=title,
        summary=summary,
        theme=theme,
        lens=lens,
        project=project or None,
        value_tags=_parse_enum_list(value_tags, ValueTag),
        artifact_tags=_parse_enum_list(artifact_tags, ArtifactType),
        references=[line.strip() for line in (references or "").splitlines() if line.strip()],
    )
    try:
        await ledger_service.log_entry(payload, source="web-ledger", actor="memory-router")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to record ledger entry: {exc}",
        ) from exc

    return RedirectResponse(url="/ledger", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/api/drive/children")
async def api_drive_children(path: Optional[str] = None, drive_id: Optional[str] = None) -> JSONResponse:
    """
    JSON API for listing items in a drive (defaults to configured drive).
    """
    selected_drive_id = drive_id or graph_client.settings.drive_id
    use_default_drive = selected_drive_id == graph_client.settings.drive_id and drive_id is None
    base_folder = None if use_default_drive else ""

    logger.info(
        "API drive listing drive=%s path=%s", selected_drive_id, path or "/"
    )
    try:
        items = await graph_client.list_children(
            path,
            drive_id=selected_drive_id,
            base_folder=base_folder,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list drive items: {exc}",
        ) from exc

    return JSONResponse(content={"path": path or "", "drive_id": selected_drive_id, "items": items})


@app.get("/api/drives")
async def api_list_drives() -> JSONResponse:
    logger.info("API drive list requested")
    try:
        drives = await graph_client.list_available_drives()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list drives: {exc}",
        ) from exc
    return JSONResponse(content={"drives": drives})


@app.get("/drive/download/{item_id}")
async def download_drive_item(item_id: str, drive_id: Optional[str] = None) -> StreamingResponse:
    logger.info("Download requested item=%s drive=%s", item_id, drive_id or "default")
    try:
        content, content_type, filename = await graph_client.download_item(
            item_id,
            drive_id=drive_id,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download file: {exc}",
        ) from exc

    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.post("/api/ledger", response_model=LedgerEntryNormalized)
async def api_log_ledger(payload: LedgerEntryCreate) -> LedgerEntryNormalized:
    try:
        entry = await ledger_service.log_entry(payload, source="api-ledger", actor="api")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to record ledger entry: {exc}",
        ) from exc
    return entry


@app.get("/api/ledger", response_model=List[LedgerEntryNormalized])
async def api_list_ledger_entries() -> List[LedgerEntryNormalized]:
    return ledger_service.list_entries()


@app.post("/api/todos", response_model=TodoEntryNormalized)
async def api_create_todo(payload: TodoEntryCreate) -> TodoEntryNormalized:
    try:
        return await todo_service.add_entry(payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to record todo: {exc}",
        ) from exc


@app.get("/api/todos", response_model=List[TodoEntryNormalized])
async def api_list_todos() -> List[TodoEntryNormalized]:
    return todo_service.list_entries()


@app.get("/entries", response_class=HTMLResponse)
async def list_entries_view(request: Request) -> HTMLResponse:
    # Newest first
    entries = sorted(IN_MEMORY_ENTRIES, key=lambda e: e.created_at, reverse=True)
    return templates.TemplateResponse(
        "entries.html",
        {
            "request": request,
            "entries": entries,
        },
    )


@app.get("/api/entries", response_model=List[EntryNormalized])
async def list_entries_api() -> List[EntryNormalized]:
    return sorted(IN_MEMORY_ENTRIES, key=lambda e: e.created_at, reverse=True)


@app.post("/submit", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    content: str = Form(...),
    project: Optional[str] = Form(default=None),
    category: EntryCategory = Form(default=EntryCategory.NOTE),
    tags: Optional[str] = Form(default=None),
    progress_stage: Optional[str] = Form(default=None),
    progress_notes: Optional[str] = Form(default=None),
) -> RedirectResponse:
    tags_list: List[str] = []
    if tags:
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    payload = EntryCreate(
        project=project or None,
        category=category,
        content_raw=content,
        tags=tags_list,
        progress_stage=progress_stage or None,
        progress_notes=progress_notes or None,
    )
    entry = build_normalized_entry(payload, source="web_form")

    logger.info("Submitting entry via web form project=%s category=%s", project, category)
    try:
        item_id = await graph_client.upload_entry(entry)
    except Exception as exc:  # pragma: no cover - simple error mapping
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload to SharePoint: {exc}",
        ) from exc

    IN_MEMORY_ENTRIES.append(entry)
    await _record_ledger_for_entry(entry, item_id=item_id, source="web_form")

    return RedirectResponse(url="/entries", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/api/entries", response_model=EntryNormalized)
async def create_entry_api(payload: EntryCreate) -> EntryNormalized:
    entry = build_normalized_entry(payload, source="api")

    logger.info("API entry submission project=%s category=%s", payload.project, payload.category)
    try:
        item_id = await graph_client.upload_entry(entry)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload to SharePoint: {exc}",
        ) from exc

    IN_MEMORY_ENTRIES.append(entry)
    await _record_ledger_for_entry(entry, item_id=item_id, source="api")
    return entry


@app.post("/api/projects/{project_name}/progress", response_model=EntryNormalized)
async def log_project_progress(
    project_name: str,
    stage: str,
    note: str,
) -> EntryNormalized:
    """
    Built-in convention endpoint for project progress logging.

    This wraps the generic entry creation with:
      - category=progress
      - project derived from the path
      - stage + note captured in dedicated fields
    """
    payload = EntryCreate(
        project=project_name,
        category=EntryCategory.PROGRESS,
        content_raw=note,
        tags=[],
        progress_stage=stage,
        progress_notes=note,
    )
    entry = build_normalized_entry(payload, source="api-progress")

    logger.info(
        "Progress entry submission project=%s stage=%s", project_name, stage
    )
    try:
        item_id = await graph_client.upload_entry(entry)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload to SharePoint: {exc}",
        ) from exc

    IN_MEMORY_ENTRIES.append(entry)
    await _record_ledger_for_entry(entry, item_id=item_id, source="api-progress")
    return entry


@app.get("/health")
async def health() -> dict:
    """
    Basic health check including Graph connectivity.
    """
    graph_ok = False
    try:
        graph_ok = await graph_client.health_check()
    except Exception:
        graph_ok = False

    outcome = {
        "status": "ok" if graph_ok else "degraded",
        "graph": "ok" if graph_ok else "unreachable",
    }
    logger.info("Health check result: %s", outcome)
    return outcome


@app.get("/api/tools", response_model=List[ToolSpec])
async def api_list_tools() -> List[ToolSpec]:
    return tool_registry.list_tools()


@app.put("/api/tools/{tool_id}", response_model=ToolSpec)
async def api_upsert_tool(tool_id: str, payload: ToolCreate) -> ToolSpec:
    if payload.id != tool_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tool_id mismatch")
    spec = tool_registry.upsert(payload)
    save_tools()
    return spec


@app.delete("/api/tools/{tool_id}")
async def api_delete_tool(tool_id: str) -> JSONResponse:
    tool_registry.delete(tool_id)
    save_tools()
    return JSONResponse(content={"ok": True})


@app.post("/api/tools/{tool_id}/run", response_model=ToolRunResult)
async def api_run_tool(tool_id: str, payload: ToolRunRequest) -> ToolRunResult:
    return tool_registry.run(tool_id, payload)


@app.get("/api/git/status")
async def api_git_status() -> JSONResponse:
    """Return git status for the local repo this service is running from."""
    try:
        status_data = get_status(_repo_root())
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return JSONResponse(content=status_data)


@app.post("/api/git/fetch")
async def api_git_fetch() -> JSONResponse:
    try:
        result = fetch(_repo_root())
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return JSONResponse(content=result)


@app.post("/api/git/pull")
async def api_git_pull() -> JSONResponse:
    """Pull changes from origin using rebase.

    If conflicts occur, the endpoint returns 409 and includes the list of conflicted files.
    """
    try:
        result = pull_rebase(_repo_root())
        return JSONResponse(content=result)
    except GitError as exc:
        # Distinguish conflicts from other errors.
        try:
            files = conflict_files(_repo_root())
        except Exception:
            files = []
        if files:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": str(exc), "conflicts": files},
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/api/git/push")
async def api_git_push() -> JSONResponse:
    try:
        result = push(_repo_root())
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return JSONResponse(content=result)


@app.get("/api/git/conflicts")
async def api_git_conflicts() -> JSONResponse:
    try:
        files = conflict_files(_repo_root())
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return JSONResponse(content={"conflicts": files})


@app.get("/api/git/conflicts/preview")
async def api_git_conflict_preview(path: str) -> JSONResponse:
    """Preview a conflicted file (first ~200 lines) to help manual resolution."""
    try:
        preview = conflict_markers_preview(_repo_root(), path)
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return JSONResponse(content={"path": path, "preview": preview})
