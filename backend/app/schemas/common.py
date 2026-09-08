from typing import Any


def ok(data: Any = None, message: str = "操作成功") -> dict[str, Any]:
    return {"success": True, "data": data, "message": message, "error": None}


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
