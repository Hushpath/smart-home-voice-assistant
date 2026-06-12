from typing import Any


def success_response(data: Any = None, message: str = "操作成功", code: str = "OK") -> dict[str, Any]:
    return {
        "success": True,
        "code": code,
        "message": message,
        "data": data if data is not None else {},
    }


def error_response(code: str, message: str, data: Any = None) -> dict[str, Any]:
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": data,
    }
