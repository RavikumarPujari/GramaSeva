from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.users import Profile
from app.models.issues import Notification
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["In-App Notifications"])

class NotificationItem(BaseModel):
    id: str
    issue_id: Optional[str] = None
    event_type: str
    title: str
    message: str
    locale: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    unread_count: int
    items: List[NotificationItem]

@router.get("", response_model=NotificationListResponse)
def get_user_notifications(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns in-app notifications for the authenticated user, newest first."""
    notifications = (
        db.query(Notification)
        .filter(Notification.profile_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    unread_count = (
        db.query(Notification)
        .filter(Notification.profile_id == current_user.id, Notification.is_read == False)
        .count()
    )

    return NotificationListResponse(
        unread_count=unread_count,
        items=[NotificationItem.model_validate(n) for n in notifications],
    )

@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks a single notification as read."""
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.profile_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.is_read = True
    db.commit()
    return {"status": "success", "id": notification_id, "is_read": True}

@router.post("/read-all")
def mark_all_notifications_read(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks all unread notifications for current user as read."""
    updated = (
        db.query(Notification)
        .filter(Notification.profile_id == current_user.id, Notification.is_read == False)
        .update({"is_read": True})
    )
    db.commit()
    return {"status": "success", "marked_read_count": updated}
