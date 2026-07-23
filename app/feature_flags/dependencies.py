from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.common.database import SessionDeep
from app.feature_flags.services import can_edit_flags
from app.users.models import User


async def require_flag_editor(
    db: SessionDeep, current_user: User = Depends(get_current_user)
) -> User:
    """admin/super_admin o cualquier usuario en la lista de editores de flags."""
    if not can_edit_flags(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar feature flags",
        )
    return current_user
