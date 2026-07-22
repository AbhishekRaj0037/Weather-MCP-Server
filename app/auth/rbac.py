import structlog
from fastapi import Depends, HTTPException, status

from app.auth.router import get_current_user
from app.auth.models import User

logger = structlog.get_logger(__name__)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        logger.warning(
            "rbac.access_denied",
            user_id=user.id,
            email=user.email,
            required_role="admin",
            actual_role=user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    logger.info(
        "rbac.access_granted",
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    return user
