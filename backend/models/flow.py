from sqlalchemy import Column, String, Boolean, DateTime, JSON
from backend.db.database import Base

class Flow(Base):
    __tablename__ = "flows"

    flow_id = Column(String(32), primary_key=True)
    flow_name = Column(String(64), nullable=False)
    business_type = Column(String(32), nullable=False)
    current_version = Column(String(32), nullable=True)
    schema = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=True)