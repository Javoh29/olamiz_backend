"""SSR-витрина (Jinja2, SEO). Пока страница-заглушка.

SEO-маршруты (/c/{category_slug}, /l/{listing_slug}, /s/{supplier_slug},
sitemap.xml, robots.txt) появятся вместе с domain/catalog — backend.md §7.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")
