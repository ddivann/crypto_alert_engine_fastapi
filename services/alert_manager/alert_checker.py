"""
Alert checker - Business logic for evaluating alert conditions.
Implements deduplication and throttling.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from shared.schemas import PriceTickMessage, AlertTriggeredMessage, AlertCondition
from shared.utils import setup_logging, now_utc
from .models import AlertRule, AlertHistory, AlertConditionEnum


logger = setup_logging()


class AlertChecker:
    """Checks price ticks against alert rules and triggers alerts."""
    
    STREAM_NAME = "alert.triggered"
    THROTTLE_MINUTES = 60  # Don't trigger same alert within 60 minutes
    
    def __init__(self, session_maker: async_sessionmaker, redis_client: aioredis.Redis):
        self.session_maker = session_maker
        self.redis = redis_client
        self._triggered_count = 0
    
    async def check_alerts(self, price_tick: PriceTickMessage):
        """
        Check if price tick triggers any alert rules.
        
        Args:
            price_tick: Price data to check against alert rules
        """
        async with self.session_maker() as session:
            # Get active alerts for this symbol
            result = await session.execute(
                select(AlertRule).where(
                    AlertRule.symbol == price_tick.symbol.upper(),
                    AlertRule.exchange == price_tick.exchange.lower(),
                    AlertRule.is_active == True
                )
            )
            alerts = result.scalars().all()
            
            for alert in alerts:
                if await self._should_trigger(alert, price_tick, session):
                    await self._trigger_alert(alert, price_tick, session)
    
    async def _should_trigger(
        self,
        alert: AlertRule,
        price_tick: PriceTickMessage,
        session: AsyncSession
    ) -> bool:
        """
        Determine if an alert should be triggered.
        Checks condition and throttling.
        """
        # Check if condition is met
        condition_met = False
        
        if alert.condition == AlertConditionEnum.ABOVE:
            condition_met = price_tick.price > alert.threshold
        elif alert.condition == AlertConditionEnum.BELOW:
            condition_met = price_tick.price < alert.threshold
        elif alert.condition == AlertConditionEnum.PERCENT_CHANGE:
            # For MVP, we'll skip percent change implementation
            # Would require historical price tracking
            pass
        
        if not condition_met:
            return False
        
        # Check throttling - don't trigger if recently triggered
        if alert.last_triggered_at:
            time_since_last = now_utc() - alert.last_triggered_at
            if time_since_last < timedelta(minutes=self.THROTTLE_MINUTES):
                return False
        
        return True
    
    async def _trigger_alert(
        self,
        alert: AlertRule,
        price_tick: PriceTickMessage,
        session: AsyncSession
    ):
        """
        Trigger an alert by publishing to Redis and updating database.
        """
        try:
            # Create alert message
            condition_text = {
                AlertConditionEnum.ABOVE: "above",
                AlertConditionEnum.BELOW: "below"
            }
            
            message = (
                f"{alert.symbol} price (${price_tick.price:,.2f}) is now "
                f"{condition_text.get(alert.condition, alert.condition.value)} "
                f"your threshold of ${alert.threshold:,.2f}"
            )
            
            alert_message = AlertTriggeredMessage(
                alert_id=alert.id,
                user_id=alert.user_id,
                symbol=alert.symbol,
                condition=AlertCondition(alert.condition.value),
                threshold=alert.threshold,
                current_price=price_tick.price,
                message=message
            )
            
            # Publish to Redis Stream
            message_data = alert_message.model_dump()
            message_data["timestamp"] = message_data["timestamp"].isoformat()
            
            await self.redis.xadd(
                self.STREAM_NAME,
                {"data": json.dumps(message_data)},
                maxlen=10000
            )
            
            # Update alert last triggered time
            alert.last_triggered_at = now_utc()
            
            # Save to history
            history = AlertHistory(
                alert_rule_id=alert.id,
                user_id=alert.user_id,
                symbol=alert.symbol,
                condition=alert.condition,
                threshold=alert.threshold,
                triggered_price=price_tick.price,
                message=message
            )
            session.add(history)
            
            await session.commit()
            
            self._triggered_count += 1
            logger.info(f"Triggered alert {alert.id} for user {alert.user_id}: {message}")
        
        except Exception as e:
            logger.error(f"Error triggering alert: {e}", exc_info=True)
            await session.rollback()
    
    def get_triggered_count(self) -> int:
        """Get total number of alerts triggered."""
        return self._triggered_count
