"""Профиль клиента: чтение и частичное обновление (backend.md §5)."""

from fastapi import APIRouter

from app.api.v1.deps import CurrentUser, SessionDep
from app.api.v1.schemas import MeOut, MePatchIn
from app.domain.users import service

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut)
async def get_me(user: CurrentUser) -> MeOut:
    return MeOut.model_validate(user)


@router.patch("/me", response_model=MeOut)
async def patch_me(payload: MePatchIn, user: CurrentUser, session: SessionDep) -> MeOut:
    await service.update_profile(session, user, name=payload.name, language=payload.language)
    await session.commit()
    return MeOut.model_validate(user)
