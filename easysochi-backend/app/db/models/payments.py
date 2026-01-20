import enum
from sqlalchemy import String, Enum, Integer, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime
from datetime import datetime
from app.db.db import Base


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    waiting_for_capture = "waiting_for_capture"
    succeeded = "succeeded"
    canceled = "canceled"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # данные ЮKassa
    yk_payment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # в копейках
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False)
    confirmation_url: Mapped[str | None] = mapped_column(Text)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)

    extradata: Mapped[dict | None] = mapped_column(JSON)

    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # связи
    user: Mapped["User"] = relationship(back_populates="payments")

    events: Mapped[list["PaymentEvent"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan"
    )
