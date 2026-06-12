from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Scene, User
from app.services.home_actions import run_scene_actions
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/scenes", tags=["场景"])


def serialize_scene(scene: Scene) -> dict:
    return {
        "id": scene.id,
        "name": scene.name,
        "description": scene.description,
        "home_id": scene.home_id,
        "actions": [
            {
                "id": action.id,
                "device_id": action.device_id,
                "device_name": action.device.name if action.device else None,
                "action": action.action,
                "target_state": action.target_state,
                "sort_order": action.sort_order,
            }
            for action in sorted(scene.actions, key=lambda item: item.sort_order)
        ],
    }


def get_user_scene(db: Session, user: User, scene_id: int) -> Scene:
    scene = (
        db.query(Scene)
        .filter(Scene.id == scene_id, Scene.home_id == user.home_id)
        .first()
    )
    if scene is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("SCENE_NOT_FOUND", "未找到指定场景"),
        )
    return scene


@router.get("", summary="查询场景列表")
def list_scenes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenes = (
        db.query(Scene)
        .filter(Scene.home_id == current_user.home_id)
        .order_by(Scene.id.asc())
        .all()
    )
    return success_response(data=[serialize_scene(scene) for scene in scenes])


@router.post("/{scene_id}/run", summary="执行场景")
def run_scene(
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scene = get_user_scene(db, current_user, scene_id)
    changes = run_scene_actions(db, current_user, scene, "scene")
    db.commit()
    return success_response(
        data={"scene": {"id": scene.id, "name": scene.name}, "changes": changes},
        message="场景执行成功",
    )
