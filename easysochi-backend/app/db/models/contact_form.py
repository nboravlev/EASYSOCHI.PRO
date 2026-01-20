from sqlalchemy import Column, Integer, String, DateTime, func
from app.db.db import Base
from datetime import datetime

class ContactForm(Base):
    __tablename__ = "contact_form"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    message = Column(String(2000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)