"""
Alert Manager Service - Main Application
Manages alert rules and evaluates price data against user-defined conditions.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from shared.config import get_settings
from shared.utils import setup_logging
from shared.schemas import AlertCondition
from .models import Base, AlertRule, AlertConditionEnum
from .consumer import RedisConsumer
from .alert_checker import AlertChecker


logger = setup_logging()
settings = get_settings()


# Global state
redis_client: aioredis.Redis = None
engine = None
async_session_maker = None
consumer: RedisConsumer = None
alert_checker: AlertChecker = None
background_tasks = set()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    global redis_client, engine, async_session_maker, consumer, alert_checker
    
    logger.info("Starting Alert Manager Service")
    
    # Initialize database
    engine = create_async_engine(settings.postgres_url, echo=settings.debug)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
    
    # Initialize Redis
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    await redis_client.ping()
    logger.info("Connected to Redis")
    
    # Initialize alert checker
    alert_checker = AlertChecker(async_session_maker, redis_client)
    
    # Initialize consumer
    consumer = RedisConsumer(redis_client, alert_checker)
    
    # Start consumer in background
    task = asyncio.create_task(consumer.start())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    
    logger.info("Alert Manager Service started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Alert Manager Service")
    await consumer.stop()
    
    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    
    await redis_client.close()
    await engine.dispose()
    logger.info("Alert Manager Service stopped")


app = FastAPI(
    title="Alert Manager Service",
    description="Manages user alert rules and evaluates conditions",
    version="1.0.0",
    lifespan=lifespan
)


# Dependency to get database session
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


# Pydantic models for API
class AlertRuleCreate(BaseModel):
    """Request model for creating alert rule."""
    user_id: int = Field(..., gt=0)
    symbol: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(default="binance", max_length=20)
    condition: AlertCondition
    threshold: float = Field(..., gt=0)


class AlertRuleResponse(BaseModel):
    """Response model for alert rule."""
    id: int
    user_id: int
    symbol: str
    exchange: str
    condition: str
    threshold: float
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "alert-manager",
        "redis_connected": redis_client is not None,
        "database_connected": engine is not None
    }


@app.post("/alerts", response_model=AlertRuleResponse)
async def create_alert(alert: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    """Create a new alert rule."""
    try:
        # Convert AlertCondition enum to AlertConditionEnum
        condition_map = {
            AlertCondition.ABOVE: AlertConditionEnum.ABOVE,
            AlertCondition.BELOW: AlertConditionEnum.BELOW,
            AlertCondition.PERCENT_CHANGE: AlertConditionEnum.PERCENT_CHANGE
        }
        
        db_alert = AlertRule(
            user_id=alert.user_id,
            symbol=alert.symbol.upper(),
            exchange=alert.exchange.lower(),
            condition=condition_map[alert.condition],
            threshold=alert.threshold
        )
        db.add(db_alert)
        await db.commit()
        await db.refresh(db_alert)
        
        logger.info(f"Created alert rule: {db_alert.id} for user {alert.user_id}")
        
        return AlertRuleResponse(
            id=db_alert.id,
            user_id=db_alert.user_id,
            symbol=db_alert.symbol,
            exchange=db_alert.exchange,
            condition=db_alert.condition.value,
            threshold=db_alert.threshold,
            is_active=db_alert.is_active,
            created_at=db_alert.created_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Error creating alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create alert")


@app.get("/alerts/{user_id}", response_model=List[AlertRuleResponse])
async def get_user_alerts(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get all alert rules for a user."""
    try:
        result = await db.execute(
            select(AlertRule).where(AlertRule.user_id == user_id)
        )
        alerts = result.scalars().all()
        
        return [
            AlertRuleResponse(
                id=alert.id,
                user_id=alert.user_id,
                symbol=alert.symbol,
                exchange=alert.exchange,
                condition=alert.condition.value,
                threshold=alert.threshold,
                is_active=alert.is_active,
                created_at=alert.created_at.isoformat()
            )
            for alert in alerts
        ]
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an alert rule."""
    try:
        result = await db.execute(
            select(AlertRule).where(AlertRule.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        await db.delete(alert)
        await db.commit()
        
        logger.info(f"Deleted alert rule: {alert_id}")
        return {"status": "deleted", "alert_id": alert_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete alert")


@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "service": "alert-manager",
        "messages_processed": consumer.get_message_count() if consumer else 0,
        "alerts_triggered": alert_checker.get_triggered_count() if alert_checker else 0,
        "redis_connected": redis_client is not None,
        "database_connected": engine is not None
    }
