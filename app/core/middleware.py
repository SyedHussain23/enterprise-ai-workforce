from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

from app.core.logger import logger


async def error_handling_middleware(request: Request, call_next):

    try:
        response = await call_next(request)
        return response

    except Exception as e:

        error = traceback.format_exc()

        logger.error(f"🔥 ERROR: {error}")

        return JSONResponse(
            status_code=500,
            content={
                "answer": "Internal server error",
                "error": str(e)
            }
        )