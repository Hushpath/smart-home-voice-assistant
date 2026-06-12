from fastapi import APIRouter, Query

from app.services.home_actions import get_weather
from app.utils.response import success_response


router = APIRouter(prefix="/weather", tags=["天气"])


@router.get("", summary="查询天气")
def weather(city: str | None = Query(default=None, description="城市名称")):
    return success_response(data=get_weather(city))
