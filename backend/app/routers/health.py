from fastapi import APIRouter

from app.core.config import settings
from app.utils.response import success_response


router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="健康检查")
def health_check():
    return success_response(
        data={
            "status": "ok",
            "service": settings.app_name,
        }
    )
