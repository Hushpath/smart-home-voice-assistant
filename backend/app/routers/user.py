from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.user import DeviceAliasCreateRequest, UserPreferenceUpdateRequest
from app.services.home_actions import BusinessError
from app.services.personalization import (
    build_preference_suggestions,
    create_device_alias,
    delete_device_alias,
    get_or_create_preferences,
    list_aliases_for_user,
    list_frequent_commands,
    serialize_alias,
    serialize_preferences,
)
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/user", tags=["用户个性化"])


@router.get("/preferences", summary="获取当前用户偏好")
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preference = get_or_create_preferences(db, current_user)
    return success_response(data=serialize_preferences(preference), message="获取用户偏好成功")


@router.get("/preference-suggestions", summary="获取偏好自动学习建议")
def get_preference_suggestions(
    limit: int = Query(default=20, ge=5, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return success_response(data=build_preference_suggestions(db, current_user, limit), message="获取偏好学习建议成功")


@router.patch("/preferences", summary="更新当前用户偏好")
def update_preferences(
    payload: UserPreferenceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preference = get_or_create_preferences(db, current_user)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(preference, key, value)
    db.add(preference)
    db.commit()
    db.refresh(preference)
    return success_response(data=serialize_preferences(preference), message="用户偏好已保存")


@router.get("/device-aliases", summary="获取设备别名")
def get_device_aliases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    aliases = list_aliases_for_user(db, current_user)
    return success_response(data=[serialize_alias(alias) for alias in aliases], message="获取设备别名成功")


@router.post("/device-aliases", summary="新增设备别名")
def add_device_alias(
    payload: DeviceAliasCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        alias = create_device_alias(db, current_user, payload.device_id, payload.alias)
    except BusinessError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_response(exc.code, exc.message, exc.data),
        ) from exc
    return success_response(data=serialize_alias(alias), message="设备别名已保存")


@router.delete("/device-aliases/{alias_id}", summary="删除设备别名")
def remove_device_alias(
    alias_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        delete_device_alias(db, current_user, alias_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_response(exc.code, exc.message, exc.data),
        ) from exc
    return success_response(message="设备别名已删除")


@router.get("/frequent-commands", summary="获取常用指令")
def get_frequent_commands(
    limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return success_response(data=list_frequent_commands(db, current_user, limit), message="获取常用指令成功")
