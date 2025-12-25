# path: app/core/deps.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from starlette import status
import jwt
from jwt import ExpiredSignatureError, InvalidSignatureError, InvalidTokenError
from typing import Dict, Any
from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=True)
ALGORITHM = "HS256"

def get_current_user_id(token=Depends(bearer_scheme)) -> int:
    try:
        payload: Dict[str, Any] = jwt.decode(
            token.credentials, settings.JWT_SECRET, algorithms=[ALGORITHM]
        )
        sub = payload.get("sub")
        if not sub:
            raise InvalidTokenError("missing sub")
        return int(sub)
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except (InvalidSignatureError, InvalidTokenError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
