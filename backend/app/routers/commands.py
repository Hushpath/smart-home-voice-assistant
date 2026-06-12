from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import CommandLog, User
from app.schemas.command import CommandExecuteRequest, CommandParseRequest
from app.services.command_executor import CommandExecutor
from app.services.command_parser import CommandParser
from app.services.home_actions import BusinessError
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/commands", tags=["中文指令"])
parser = CommandParser()


@router.post("/parse", summary="解析中文指令")
def parse_command(
    payload: CommandParseRequest,
    current_user: User = Depends(get_current_user),
):
    result = parser.parse(payload.command)
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_COMMAND", result.message, result.to_dict()),
        )
    return success_response(data=result.to_dict(), message="解析成功")


def serialize_command_log(log: CommandLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "raw_command": log.raw_command,
        "parsed_result": log.parsed_result,
        "execution_result": log.execution_result,
        "success": log.success,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.post("/execute", summary="执行中文指令")
def execute_command(
    payload: CommandExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    executor = CommandExecutor(db=db, user=current_user)
    try:
        result = executor.execute(payload.command)
    except BusinessError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_response(exc.code, exc.message, exc.data),
        ) from exc
    return success_response(data=result, message="指令执行成功")


@router.get("/logs", summary="查询指令执行日志")
def list_command_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = (
        db.query(CommandLog)
        .filter(CommandLog.user_id == current_user.id)
        .order_by(CommandLog.id.desc())
        .all()
    )
    return success_response(data=[serialize_command_log(log) for log in logs])
