"""Admin-only route guards (user_id from client session)."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.src.db import models
from backend.src.utils.security import validate_integer_id


def require_admin(user_id: int, db: Session) -> models.User:
    if not validate_integer_id(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.user_type != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
