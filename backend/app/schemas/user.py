from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime, date

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1)  # Maps to full_name
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    user: dict # Contains id, name, email
    token: str

class UserDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    email: str
    name: str = Field(alias="full_name")
    avatar_url: Optional[str] = Field(alias="avatarUrl", default=None)
    daily_new_node_cap: int = Field(alias="dailyNewNodeCap", default=10)
    daily_reminder_time: Optional[str] = Field(alias="dailyReminderTime", default=None)
    session_length_pref: int = Field(alias="sessionLengthPref", default=30)
    notify_reminders: bool = Field(alias="notifyReminders", default=True)
    notify_due_reviews: bool = Field(alias="notifyDueReviews", default=True)
    notify_processing: bool = Field(alias="notifyProcessing", default=True)
    global_streak: int = Field(alias="globalStreak", default=0)
    last_active_date: Optional[str] = Field(alias="lastActiveDate", default=None)
    created_at: str = Field(alias="createdAt")

    @classmethod
    def from_orm(cls, user):
        return cls(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            avatarUrl=user.avatar_url,
            dailyNewNodeCap=user.daily_new_node_cap,
            dailyReminderTime=user.daily_reminder_time,
            sessionLengthPref=user.session_length_pref,
            notifyReminders=user.notify_reminders,
            notifyDueReviews=user.notify_due_reviews,
            notifyProcessing=user.notify_processing,
            globalStreak=user.global_streak,
            lastActiveDate=user.last_active_date.isoformat() if user.last_active_date else None,
            createdAt=user.created_at.isoformat()
        )

class UserUpdateDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    daily_new_node_cap: Optional[int] = Field(alias="dailyNewNodeCap", default=None)
    daily_reminder_time: Optional[str] = Field(alias="dailyReminderTime", default=None)
    session_length_pref: Optional[int] = Field(alias="sessionLengthPref", default=None)
    notify_reminders: Optional[bool] = Field(alias="notifyReminders", default=None)
    notify_due_reviews: Optional[bool] = Field(alias="notifyDueReviews", default=None)
    notify_processing: Optional[bool] = Field(alias="notifyProcessing", default=None)
