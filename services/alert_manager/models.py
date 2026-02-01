"""
Database models for Alert Manager service.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class AlertConditionEnum(str, enum.Enum):
    """Alert condition types."""
    ABOVE = "above"
    BELOW = "below"
    PERCENT_CHANGE = "percent_change"


class AlertRule(Base):
    """User-defined alert rules."""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(20), nullable=False, default="binance")
    condition = Column(SQLEnum(AlertConditionEnum), nullable=False)
    threshold = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_triggered_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<AlertRule(id={self.id}, user_id={self.user_id}, symbol={self.symbol}, condition={self.condition}, threshold={self.threshold})>"


class AlertHistory(Base):
    """History of triggered alerts for deduplication and auditing."""
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_rule_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    condition = Column(SQLEnum(AlertConditionEnum), nullable=False)
    threshold = Column(Float, nullable=False)
    triggered_price = Column(Float, nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    message = Column(String(500), nullable=False)
    
    def __repr__(self):
        return f"<AlertHistory(id={self.id}, alert_rule_id={self.alert_rule_id}, triggered_at={self.triggered_at})>"
