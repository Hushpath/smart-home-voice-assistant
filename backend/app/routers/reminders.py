from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Reminder, User
from app.schemas.reminder import ReminderCreateRequest, ReminderUpdateRequest
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/reminders", tags=["提醒"])


def serialize_reminder(reminder: Reminder) -> dict:
    return {
        "id": reminder.id,
        "user_id": reminder.user_id,
        "title": reminder.title,
        "remind_time": reminder.remind_time.isoformat() if reminder.remind_time else None,
        "is_done": reminder.is_done,
        "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
        "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None,
    }


def get_user_reminder(db: Session, user: User, reminder_id: int) -> Reminder:
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user.id)
        .first()
    )
    if reminder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("REMINDER_NOT_FOUND", "未找到指定提醒"),
        )
    return reminder


@router.get("", summary="查询提醒列表")
def list_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminders = (
        db.query(Reminder)
        .filter(Reminder.user_id == current_user.id)
        .order_by(Reminder.id.desc())
        .all()
    )
    return success_response(data=[serialize_reminder(reminder) for reminder in reminders])


@router.post("", summary="创建提醒")
def create_reminder(
    payload: ReminderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = Reminder(
        user_id=current_user.id,
        title=payload.title,
        remind_time=payload.remind_time,
        is_done=False,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return success_response(data=serialize_reminder(reminder), message="提醒创建成功")


@router.patch("/{reminder_id}", summary="修改提醒")
def update_reminder(
    reminder_id: int,
    payload: ReminderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = get_user_reminder(db, current_user, reminder_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "title" in update_data:
        reminder.title = update_data["title"]
    if "remind_time" in update_data:
        reminder.remind_time = update_data["remind_time"]
    if "is_done" in update_data:
        reminder.is_done = update_data["is_done"]
    db.commit()
    db.refresh(reminder)
    return success_response(data=serialize_reminder(reminder), message="提醒修改成功")


@router.delete("/{reminder_id}", summary="删除提醒")
def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = get_user_reminder(db, current_user, reminder_id)
    db.delete(reminder)
    db.commit()
    return success_response(data={"id": reminder_id}, message="提醒删除成功")
