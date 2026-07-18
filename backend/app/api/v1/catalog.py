"""Каталог: дерево категорий (backend.md §5). Хендлеры тонкие, логика — в domain/catalog."""

from fastapi import APIRouter

from app.api.v1.deps import SessionDep
from app.api.v1.schemas import CategoryOut
from app.domain.catalog import service

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
async def categories(session: SessionDep) -> list[CategoryOut]:
    tree = await service.list_category_tree(session)
    return [CategoryOut.model_validate(node) for node in tree]
