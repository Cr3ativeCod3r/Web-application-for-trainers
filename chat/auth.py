import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from config import SECRET_KEY

security = HTTPBearer()


def verify_token(token: str) -> int:
    """
    Validates a SimpleJWT access token issued by Django and returns the user id.

    The token_type check matters: SimpleJWT refresh tokens are signed with the same
    key and also carry user_id, but they are long-lived and must not grant access.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("token_type") != "access":
            raise InvalidTokenError("Not an access token")
        user_id = payload.get("user_id")
        if user_id is None:
            raise InvalidTokenError("Missing user_id")
        return int(user_id)
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    return verify_token(credentials.credentials)
