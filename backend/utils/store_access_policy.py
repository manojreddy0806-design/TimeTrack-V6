"""
Centralized Store Access Policy Module

This module provides authoritative business rules for store-hours access control:
- Login allowed window: store_open_time - 30 minutes to store_close_time + 45 minutes
- Clock-in/out allowed window: store_open_time - 30 minutes to store_close_time + 30 minutes
- Auto clock-out time: store_close_time + 30 minutes

All times are in store timezone (defaults to APP_TIMEZONE/America/New_York if not specified).
"""
from datetime import datetime, timedelta, time
from typing import Optional, Tuple, Dict, Any
import pytz
from backend.utils.timezone_utils import get_app_timezone, get_app_timezone_name


class StoreAccessPolicy:
    """Centralized policy for store-hours access control"""
    
    # Policy constants
    LOGIN_EARLY_BUFFER_MINUTES = 30  # Login allowed 30 min before opening
    LOGIN_LATE_BUFFER_MINUTES = 45   # Login allowed 45 min after closing
    CLOCK_EARLY_BUFFER_MINUTES = 30  # Clock actions allowed 30 min before opening
    CLOCK_LATE_BUFFER_MINUTES = 30   # Clock actions allowed 30 min after closing
    AUTO_CLOCKOUT_DELAY_MINUTES = 30  # Auto clock-out 30 min after closing
    
    @staticmethod
    def get_store_timezone(store_timezone: Optional[str] = None) -> Tuple[pytz.BaseTzInfo, str]:
        """
        Get store timezone object. Defaults to APP_TIMEZONE (America/New_York) if not specified.
        
        Args:
            store_timezone: Timezone string (e.g., 'America/New_York') or None
            
        Returns:
            Tuple of (pytz timezone object, timezone name string)
        """
        if store_timezone:
            try:
                tz_obj = pytz.timezone(store_timezone)
                return tz_obj, store_timezone
            except pytz.exceptions.UnknownTimeZoneError:
                # Invalid timezone, default to APP_TIMEZONE
                app_tz = get_app_timezone()
                return app_tz, get_app_timezone_name()
        # Default to APP_TIMEZONE instead of UTC
        app_tz = get_app_timezone()
        return app_tz, get_app_timezone_name()
    
    @staticmethod
    def parse_time_string(time_str: Optional[str]) -> Optional[time]:
        """
        Parse time string in HH:MM format to time object.
        
        Args:
            time_str: Time string in "HH:MM" format (24-hour)
            
        Returns:
            time object or None if invalid
        """
        if not time_str:
            return None
        
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return None
            return time(hour, minute)
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def get_store_time_now(store_timezone: Optional[str] = None) -> datetime:
        """
        Get current time in store timezone.
        
        Args:
            store_timezone: Store timezone string or None for UTC
            
        Returns:
            datetime in store timezone (timezone-aware)
        """
        tz = StoreAccessPolicy.get_store_timezone(store_timezone)
        return datetime.now(tz)
    
    @staticmethod
    def get_today_schedule_datetime(
        time_obj: time,
        store_timezone: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Convert a time object to a datetime for today in store timezone.
        Handles overnight stores (close time < open time).
        
        Args:
            time_obj: time object (e.g., time(9, 0))
            store_timezone: Store timezone string or None
            reference_time: Reference datetime (defaults to now in store timezone)
            
        Returns:
            datetime in store timezone or None if invalid
        """
        if not time_obj:
            return None
        
        tz, _ = StoreAccessPolicy.get_store_timezone(store_timezone)
        if reference_time is None:
            reference_time = datetime.now(tz)
        else:
            # Ensure reference_time is in store timezone
            if reference_time.tzinfo is None:
                reference_time = tz.localize(reference_time)
            else:
                reference_time = reference_time.astimezone(tz)
        
        # Create datetime for today at the specified time
        schedule_dt = reference_time.replace(
            hour=time_obj.hour,
            minute=time_obj.minute,
            second=0,
            microsecond=0
        )
        
        return schedule_dt
    
    @staticmethod
    def can_login(
        now: Optional[datetime] = None,
        opening_time: Optional[str] = None,
        closing_time: Optional[str] = None,
        store_timezone: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Check if login is allowed based on store hours.
        
        Login allowed window: opening_time - 30 minutes to closing_time + 45 minutes
        
        Args:
            now: Current datetime (defaults to now in store timezone)
            opening_time: Store opening time string "HH:MM" (24-hour)
            closing_time: Store closing time string "HH:MM" (24-hour)
            store_timezone: Store timezone string or None for UTC
            
        Returns:
            Tuple of (allowed: bool, reason: str or None, metadata: dict or None)
            Metadata includes window_start, window_end, current_time for UI display
        """
        # If no store hours configured, allow login (backward compatibility)
        if not opening_time or not closing_time:
            return True, None, None
        
        # Parse times
        open_time = StoreAccessPolicy.parse_time_string(opening_time)
        close_time = StoreAccessPolicy.parse_time_string(closing_time)
        
        if not open_time or not close_time:
            return True, None, None  # Invalid times, allow (backward compatibility)
        
        # Get current time in store timezone
        tz, tz_name = StoreAccessPolicy.get_store_timezone(store_timezone)
        if now is None:
            now = datetime.now(tz)
        else:
            # Convert to store timezone if needed
            if now.tzinfo is None:
                now = tz.localize(now)
            else:
                now = now.astimezone(tz)
        
        # Get today's schedule times
        open_dt = StoreAccessPolicy.get_today_schedule_datetime(open_time, store_timezone, now)
        close_dt = StoreAccessPolicy.get_today_schedule_datetime(close_time, store_timezone, now)
        
        if not open_dt or not close_dt:
            return True, None, None
        
        # Handle overnight stores (close time < open time means close is next day)
        # Example: 20:00-02:00 means close at 02:00 next day
        if close_time < open_time:
            # Closing time is tomorrow - add one day
            close_dt = close_dt + timedelta(days=1)
            
            # For overnight stores, we need to handle the case where "now" might be
            # before midnight but after the previous day's close time
            # If now is before open_dt today, check if we're in the previous day's window
            if now < open_dt:
                # Check if we're in yesterday's window (close_dt - 1 day)
                prev_close_dt = close_dt - timedelta(days=1)
                prev_window_end = prev_close_dt + timedelta(minutes=StoreAccessPolicy.LOGIN_LATE_BUFFER_MINUTES)
                prev_window_start = (open_dt - timedelta(days=1)) - timedelta(minutes=StoreAccessPolicy.LOGIN_EARLY_BUFFER_MINUTES)
                
                if prev_window_start <= now <= prev_window_end:
                    metadata = {
                        'window_start': prev_window_start.isoformat(),
                        'window_end': prev_window_end.isoformat(),
                        'current_time': now.isoformat(),
                        'store_timezone': tz_name,
                        'opening_time': opening_time,
                        'closing_time': closing_time
                    }
                    return True, None, metadata
        
        # Calculate login window with buffers
        login_window_start = open_dt - timedelta(minutes=StoreAccessPolicy.LOGIN_EARLY_BUFFER_MINUTES)
        login_window_end = close_dt + timedelta(minutes=StoreAccessPolicy.LOGIN_LATE_BUFFER_MINUTES)
        
        # Check if now is within window (inclusive boundaries)
        if login_window_start <= now <= login_window_end:
            metadata = {
                'window_start': login_window_start.isoformat(),
                'window_end': login_window_end.isoformat(),
                'current_time': now.isoformat(),
                'store_timezone': tz_name,
                'opening_time': opening_time,
                'closing_time': closing_time
            }
            return True, None, metadata
        
        # Outside window - create informative error message
        # Format times for display
        window_start_str = login_window_start.strftime('%H:%M')
        window_end_str = login_window_end.strftime('%H:%M')
        current_time_str = now.strftime('%H:%M')
        
        # Determine if before or after window
        if now < login_window_start:
            reason = (
                f"Store is closed. Login is allowed from {window_start_str} to {window_end_str} "
                f"({tz_name}). Current time: {current_time_str} ({tz_name}). "
                f"Store hours: {opening_time} - {closing_time}."
            )
        else:
            reason = (
                f"Store is closed. Login is allowed from {window_start_str} to {window_end_str} "
                f"({tz_name}). Current time: {current_time_str} ({tz_name}). "
                f"Store hours: {opening_time} - {closing_time}."
            )
        
        metadata = {
            'window_start': login_window_start.isoformat(),
            'window_end': login_window_end.isoformat(),
            'current_time': now.isoformat(),
            'store_timezone': tz_name,
            'opening_time': opening_time,
            'closing_time': closing_time,
            'error_code': 'STORE_CLOSED_LOGIN'
        }
        
        return False, reason, metadata
    
    @staticmethod
    def can_clock_action(
        now: Optional[datetime] = None,
        opening_time: Optional[str] = None,
        closing_time: Optional[str] = None,
        store_timezone: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Check if clock-in/out action is allowed based on store hours.
        
        Clock window: opening_time - 30 minutes to closing_time + 30 minutes
        
        Args:
            now: Current datetime (defaults to now in store timezone)
            opening_time: Store opening time string "HH:MM" (24-hour)
            closing_time: Store closing time string "HH:MM" (24-hour)
            store_timezone: Store timezone string or None for UTC
            
        Returns:
            Tuple of (allowed: bool, reason: str or None, metadata: dict or None)
            Metadata includes window_start, window_end, current_time for UI display
        """
        # If no store hours configured, allow clock action (backward compatibility)
        if not opening_time or not closing_time:
            return True, None, None
        
        # Parse times
        open_time = StoreAccessPolicy.parse_time_string(opening_time)
        close_time = StoreAccessPolicy.parse_time_string(closing_time)
        
        if not open_time or not close_time:
            return True, None, None  # Invalid times, allow (backward compatibility)
        
        # Get current time in store timezone
        tz, tz_name = StoreAccessPolicy.get_store_timezone(store_timezone)
        if now is None:
            now = datetime.now(tz)
        else:
            # Convert to store timezone if needed
            if now.tzinfo is None:
                now = tz.localize(now)
            else:
                now = now.astimezone(tz)
        
        # Get today's schedule times
        open_dt = StoreAccessPolicy.get_today_schedule_datetime(open_time, store_timezone, now)
        close_dt = StoreAccessPolicy.get_today_schedule_datetime(close_time, store_timezone, now)
        
        if not open_dt or not close_dt:
            return True, None, None
        
        # Handle overnight stores (close time < open time means close is next day)
        if close_time < open_time:
            # Closing time is tomorrow - add one day
            close_dt = close_dt + timedelta(days=1)
            
            # For overnight stores, handle case where "now" might be before midnight
            if now < open_dt:
                # Check if we're in yesterday's window
                prev_close_dt = close_dt - timedelta(days=1)
                prev_window_end = prev_close_dt + timedelta(minutes=StoreAccessPolicy.CLOCK_LATE_BUFFER_MINUTES)
                prev_window_start = (open_dt - timedelta(days=1)) - timedelta(minutes=StoreAccessPolicy.CLOCK_EARLY_BUFFER_MINUTES)
                
                if prev_window_start <= now <= prev_window_end:
                    metadata = {
                        'window_start': prev_window_start.isoformat(),
                        'window_end': prev_window_end.isoformat(),
                        'current_time': now.isoformat(),
                        'store_timezone': tz_name,
                        'opening_time': opening_time,
                        'closing_time': closing_time
                    }
                    return True, None, metadata
        
        # Calculate clock window with buffers
        clock_window_start = open_dt - timedelta(minutes=StoreAccessPolicy.CLOCK_EARLY_BUFFER_MINUTES)
        clock_window_end = close_dt + timedelta(minutes=StoreAccessPolicy.CLOCK_LATE_BUFFER_MINUTES)
        
        # Check if now is within window (inclusive boundaries)
        if clock_window_start <= now <= clock_window_end:
            metadata = {
                'window_start': clock_window_start.isoformat(),
                'window_end': clock_window_end.isoformat(),
                'current_time': now.isoformat(),
                'store_timezone': tz_name,
                'opening_time': opening_time,
                'closing_time': closing_time
            }
            return True, None, metadata
        
        # Outside window - create informative error message
        window_start_str = clock_window_start.strftime('%H:%M')
        window_end_str = clock_window_end.strftime('%H:%M')
        current_time_str = now.strftime('%H:%M')
        
        reason = (
            f"Clock in/out is allowed only between {window_start_str} and {window_end_str} "
            f"({tz_name}). Current time: {current_time_str} ({tz_name}). "
            f"Store hours: {opening_time} - {closing_time}."
        )
        
        metadata = {
            'window_start': clock_window_start.isoformat(),
            'window_end': clock_window_end.isoformat(),
            'current_time': now.isoformat(),
            'store_timezone': tz_name,
            'opening_time': opening_time,
            'closing_time': closing_time,
            'error_code': 'OUTSIDE_CLOCK_WINDOW'
        }
        
        return False, reason, metadata
    
    @staticmethod
    def auto_clock_out_at(
        closing_time: Optional[str] = None,
        store_timezone: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Calculate the auto clock-out time for a store.
        
        Auto clock-out occurs at: closing_time + 30 minutes
        
        Args:
            closing_time: Store closing time string "HH:MM" (24-hour)
            store_timezone: Store timezone string or None for UTC
            reference_time: Reference datetime (defaults to now in store timezone)
            
        Returns:
            datetime when auto clock-out should occur, or None if invalid
        """
        if not closing_time:
            return None
        
        close_time = StoreAccessPolicy.parse_time_string(closing_time)
        if not close_time:
            return None
        
        tz, _ = StoreAccessPolicy.get_store_timezone(store_timezone)
        if reference_time is None:
            reference_time = datetime.now(tz)
        else:
            # Ensure reference_time is in store timezone
            if reference_time.tzinfo is None:
                reference_time = tz.localize(reference_time)
            else:
                reference_time = reference_time.astimezone(tz)
        
        # Get today's closing time
        close_dt = StoreAccessPolicy.get_today_schedule_datetime(close_time, store_timezone, reference_time)
        if not close_dt:
            return None
        
        # Handle overnight stores (close < open means close is next day)
        # We need opening_time to determine this, but for auto-clockout we'll assume
        # if close_time is early (before 6 AM), it's likely next day
        if close_time < time(6, 0):  # Heuristic: if closing before 6 AM, assume next day
            close_dt = close_dt + timedelta(days=1)
        
        # Auto clock-out is 30 minutes after closing
        auto_clockout_dt = close_dt + timedelta(minutes=StoreAccessPolicy.AUTO_CLOCKOUT_DELAY_MINUTES)
        
        return auto_clockout_dt
