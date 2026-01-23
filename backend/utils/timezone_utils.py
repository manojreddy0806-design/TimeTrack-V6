"""
Timezone utility functions for consistent ET (America/New_York) handling.

This module provides a single source of truth for timezone operations:
- All business logic uses America/New_York (ET) timezone
- Database timestamps are stored in UTC (naive datetime)
- Conversion happens at application boundary (API/UI/business rules)
"""

from datetime import datetime, timezone as dt_timezone
from typing import Optional
import pytz
from backend.config import Config

# Application timezone (ET)
APP_TZ = pytz.timezone(Config.APP_TIMEZONE)
UTC_TZ = pytz.UTC


def get_app_timezone():
    """
    Get the application timezone object (America/New_York).
    
    Returns:
        pytz timezone object for America/New_York
    """
    return APP_TZ


def get_app_timezone_name():
    """
    Get the application timezone name.
    
    Returns:
        str: "America/New_York"
    """
    return Config.APP_TIMEZONE


def now_et() -> datetime:
    """
    Get current time in ET (America/New_York), timezone-aware.
    
    This is the canonical function for getting "now" in the application.
    Use this instead of datetime.utcnow() or datetime.now().
    
    Returns:
        datetime: Current time in ET, timezone-aware
    """
    return datetime.now(APP_TZ)


def now_utc() -> datetime:
    """
    Get current time in UTC, timezone-aware.
    
    Use this when you need UTC for database storage or comparisons.
    
    Returns:
        datetime: Current time in UTC, timezone-aware
    """
    return datetime.now(UTC_TZ)


def now_utc_naive() -> datetime:
    """
    Get current time in UTC as naive datetime (for database storage).
    
    Database columns use naive datetime, assumed to be UTC.
    Use this when storing timestamps in the database.
    
    Returns:
        datetime: Current time in UTC, naive (no timezone info)
    """
    return datetime.utcnow()


def et_to_utc_naive(dt_et: datetime) -> datetime:
    """
    Convert ET datetime to UTC naive datetime (for database storage).
    
    Args:
        dt_et: datetime in ET (timezone-aware or naive)
        
    Returns:
        datetime: UTC time as naive datetime (for database storage)
    """
    if dt_et.tzinfo is None:
        # Assume naive datetime is in ET
        dt_et = APP_TZ.localize(dt_et)
    else:
        # Convert to ET if not already
        if dt_et.tzinfo != APP_TZ:
            dt_et = dt_et.astimezone(APP_TZ)
    
    # Convert to UTC and remove timezone info
    dt_utc = dt_et.astimezone(UTC_TZ)
    return dt_utc.replace(tzinfo=None)


def utc_naive_to_et(dt_utc_naive: datetime) -> datetime:
    """
    Convert UTC naive datetime (from database) to ET timezone-aware datetime.
    
    Args:
        dt_utc_naive: datetime from database (naive, assumed UTC)
        
    Returns:
        datetime: ET time, timezone-aware
    """
    # Localize naive UTC datetime
    dt_utc = UTC_TZ.localize(dt_utc_naive)
    # Convert to ET
    return dt_utc.astimezone(APP_TZ)


def et_to_utc(dt_et: datetime) -> datetime:
    """
    Convert ET datetime to UTC timezone-aware datetime.
    
    Args:
        dt_et: datetime in ET (timezone-aware or naive)
        
    Returns:
        datetime: UTC time, timezone-aware
    """
    if dt_et.tzinfo is None:
        # Assume naive datetime is in ET
        dt_et = APP_TZ.localize(dt_et)
    else:
        # Convert to ET if not already
        if dt_et.tzinfo != APP_TZ:
            dt_et = dt_et.astimezone(APP_TZ)
    
    return dt_et.astimezone(UTC_TZ)


def utc_to_et(dt_utc: datetime) -> datetime:
    """
    Convert UTC datetime to ET timezone-aware datetime.
    
    Args:
        dt_utc: datetime in UTC (timezone-aware or naive)
        
    Returns:
        datetime: ET time, timezone-aware
    """
    if dt_utc.tzinfo is None:
        # Assume naive datetime is in UTC
        dt_utc = UTC_TZ.localize(dt_utc)
    
    return dt_utc.astimezone(APP_TZ)


def today_start_et() -> datetime:
    """
    Get start of today (00:00:00) in ET, timezone-aware.
    
    Returns:
        datetime: Start of today in ET
    """
    now = now_et()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def today_start_utc_naive() -> datetime:
    """
    Get start of today (00:00:00) in UTC as naive datetime (for database queries).
    
    Returns:
        datetime: Start of today in UTC, naive
    """
    now = now_utc_naive()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)
