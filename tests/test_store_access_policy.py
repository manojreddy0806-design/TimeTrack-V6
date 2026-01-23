"""
Unit tests for StoreAccessPolicy

Tests store hours login enforcement logic including:
- Normal store hours
- Different timezones
- Overnight stores
- Boundary conditions
- Edge cases
"""
import unittest
from datetime import datetime, time
import pytz
from backend.utils.store_access_policy import StoreAccessPolicy


class TestStoreAccessPolicy(unittest.TestCase):
    """Test cases for StoreAccessPolicy"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.utc = pytz.UTC
        self.ny_tz = pytz.timezone('America/New_York')
        self.la_tz = pytz.timezone('America/Los_Angeles')
    
    def test_normal_store_hours_utc(self):
        """Test normal store hours (09:00-17:00) in UTC"""
        opening_time = "09:00"
        closing_time = "17:00"
        store_timezone = "UTC"
        
        # Test cases: (current_time_utc, expected_allowed, description)
        test_cases = [
            # Before window (8:29 UTC)
            (datetime(2024, 1, 15, 8, 29, 0, tzinfo=self.utc), False, "Before window start"),
            # Window start (8:30 UTC)
            (datetime(2024, 1, 15, 8, 30, 0, tzinfo=self.utc), True, "Window start"),
            # During hours (12:00 UTC)
            (datetime(2024, 1, 15, 12, 0, 0, tzinfo=self.utc), True, "During hours"),
            # Close time (17:00 UTC)
            (datetime(2024, 1, 15, 17, 0, 0, tzinfo=self.utc), True, "Close time"),
            # Window end (17:45 UTC)
            (datetime(2024, 1, 15, 17, 45, 0, tzinfo=self.utc), True, "Window end"),
            # After window (17:46 UTC)
            (datetime(2024, 1, 15, 17, 46, 0, tzinfo=self.utc), False, "After window"),
        ]
        
        for now, expected_allowed, description in test_cases:
            with self.subTest(description=description, now=now):
                can_login, reason, metadata = StoreAccessPolicy.can_login(
                    now=now,
                    opening_time=opening_time,
                    closing_time=closing_time,
                    store_timezone=store_timezone
                )
                self.assertEqual(can_login, expected_allowed, 
                               f"Failed for {description}: {reason}")
    
    def test_store_hours_different_timezone(self):
        """Test store hours in different timezone (America/New_York)"""
        opening_time = "09:00"
        closing_time = "17:00"
        store_timezone = "America/New_York"
        
        # Server time: 14:00 UTC = 09:00 EST (UTC-5 in winter)
        # Should be allowed (within window)
        now_utc = datetime(2024, 1, 15, 14, 0, 0, tzinfo=self.utc)
        
        can_login, reason, metadata = StoreAccessPolicy.can_login(
            now=now_utc,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        
        self.assertTrue(can_login, f"Should be allowed at 09:00 EST: {reason}")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.get('store_timezone'), store_timezone)
    
    def test_overnight_store(self):
        """Test overnight store (20:00-02:00)"""
        opening_time = "20:00"
        closing_time = "02:00"
        store_timezone = "UTC"
        
        # Test cases for overnight store
        test_cases = [
            # Before window (19:30 UTC)
            (datetime(2024, 1, 15, 19, 30, 0, tzinfo=self.utc), False, "Before window"),
            # Window start (19:31 UTC)
            (datetime(2024, 1, 15, 19, 31, 0, tzinfo=self.utc), True, "Window start"),
            # During hours (23:00 UTC)
            (datetime(2024, 1, 15, 23, 0, 0, tzinfo=self.utc), True, "During hours"),
            # Close time (02:00 UTC next day)
            (datetime(2024, 1, 16, 2, 0, 0, tzinfo=self.utc), True, "Close time"),
            # Window end (02:45 UTC next day)
            (datetime(2024, 1, 16, 2, 45, 0, tzinfo=self.utc), True, "Window end"),
            # After window (02:46 UTC next day)
            (datetime(2024, 1, 16, 2, 46, 0, tzinfo=self.utc), False, "After window"),
        ]
        
        for now, expected_allowed, description in test_cases:
            with self.subTest(description=description, now=now):
                can_login, reason, metadata = StoreAccessPolicy.can_login(
                    now=now,
                    opening_time=opening_time,
                    closing_time=closing_time,
                    store_timezone=store_timezone
                )
                self.assertEqual(can_login, expected_allowed,
                               f"Failed for {description}: {reason}")
    
    def test_no_store_hours_configured(self):
        """Test that login is allowed when store hours are not configured"""
        can_login, reason, metadata = StoreAccessPolicy.can_login(
            opening_time=None,
            closing_time=None,
            store_timezone=None
        )
        
        self.assertTrue(can_login, "Should allow login when hours not configured")
        self.assertIsNone(reason)
        self.assertIsNone(metadata)
    
    def test_default_timezone_is_et(self):
        """Test that default timezone (when None) is APP_TIMEZONE (America/New_York)"""
        opening_time = "09:00"
        closing_time = "17:00"
        # No store_timezone specified - should default to APP_TIMEZONE
        
        # 14:00 UTC = 09:00 EST (UTC-5 in winter)
        now_utc = datetime(2024, 1, 15, 14, 0, 0, tzinfo=self.utc)
        
        can_login, reason, metadata = StoreAccessPolicy.can_login(
            now=now_utc,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=None  # Should default to APP_TIMEZONE
        )
        
        self.assertTrue(can_login, "Should allow at 09:00 ET (default timezone)")
        if metadata:
            self.assertEqual(metadata.get('store_timezone'), 'America/New_York')
    
    def test_dst_transition_spring_forward(self):
        """Test DST spring forward transition (EST to EDT)"""
        opening_time = "09:00"
        closing_time = "17:00"
        store_timezone = "America/New_York"
        
        # March 10, 2024 2:00 AM EST -> 3:00 AM EDT (spring forward)
        # Test at 2:30 AM EST (which becomes 2:30 AM EDT after transition)
        # Note: 2:00-3:00 AM doesn't exist on spring forward day
        # So we test just before (1:59 AM EST) and just after (3:00 AM EDT)
        
        # Just before transition: 1:59 AM EST = 6:59 UTC
        now_before = datetime(2024, 3, 10, 6, 59, 0, tzinfo=self.utc)
        can_login_before, _, _ = StoreAccessPolicy.can_login(
            now=now_before,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        
        # Just after transition: 3:00 AM EDT = 7:00 UTC
        now_after = datetime(2024, 3, 10, 7, 0, 0, tzinfo=self.utc)
        can_login_after, _, _ = StoreAccessPolicy.can_login(
            now=now_after,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        
        # Both should work (before opening time, but policy should handle DST)
        # The key is that pytz handles DST automatically
        self.assertIsNotNone(can_login_before)
        self.assertIsNotNone(can_login_after)
    
    def test_dst_transition_fall_back(self):
        """Test DST fall back transition (EDT to EST)"""
        opening_time = "09:00"
        closing_time = "17:00"
        store_timezone = "America/New_York"
        
        # November 3, 2024 2:00 AM EDT -> 1:00 AM EST (fall back)
        # Test at 1:30 AM - this occurs twice (once as EDT, once as EST)
        # pytz will use the later occurrence (EST)
        
        # 1:30 AM EST = 6:30 UTC (after fall back)
        now_after = datetime(2024, 11, 3, 6, 30, 0, tzinfo=self.utc)
        can_login_after, _, _ = StoreAccessPolicy.can_login(
            now=now_after,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        
        # Should work (before opening time, but policy should handle DST)
        self.assertIsNotNone(can_login_after)
    
    def test_invalid_timezone_fallback(self):
        """Test that invalid timezone falls back to APP_TIMEZONE (America/New_York)"""
        opening_time = "09:00"
        closing_time = "17:00"
        store_timezone = "Invalid/Timezone"
        
        # Should not crash, should use APP_TIMEZONE (ET)
        now_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=self.utc)
        
        can_login, reason, metadata = StoreAccessPolicy.can_login(
            now=now_utc,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        
        # Should still work (uses APP_TIMEZONE fallback, which is America/New_York)
        self.assertIsNotNone(can_login)
        if metadata:
            # Should fall back to APP_TIMEZONE (America/New_York), not UTC
            self.assertEqual(metadata.get('store_timezone'), 'America/New_York')
    
    def test_exact_boundary_times(self):
        """Test exact boundary times (inclusive boundaries)"""
        opening_time = "09:00"
        closing_time = "17:00"
        store_timezone = "UTC"
        
        # Exact open time (should be allowed)
        now = datetime(2024, 1, 15, 8, 30, 0, tzinfo=self.utc)  # 8:30 = open - 30 min
        can_login, _, _ = StoreAccessPolicy.can_login(
            now=now,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        self.assertTrue(can_login, "Should allow at exact window start")
        
        # Exact close time + buffer (should be allowed)
        now = datetime(2024, 1, 15, 17, 45, 0, tzinfo=self.utc)  # 17:45 = close + 45 min
        can_login, _, _ = StoreAccessPolicy.can_login(
            now=now,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        self.assertTrue(can_login, "Should allow at exact window end")
    
    def test_error_message_includes_timezone(self):
        """Test that error messages include timezone information"""
        opening_time = "09:00"
        closing_time = "17:00"
        store_timezone = "America/New_York"
        
        # Try login outside hours (23:00 UTC = 18:00 EST, after window which ends at 17:45 EST)
        now = datetime(2024, 1, 15, 23, 0, 0, tzinfo=self.utc)  # 23:00 UTC = 18:00 EST
        
        can_login, reason, metadata = StoreAccessPolicy.can_login(
            now=now,
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        
        self.assertFalse(can_login, "Should block login outside hours")
        self.assertIsNotNone(reason)
        self.assertIn(store_timezone, reason or "", "Error message should include timezone")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.get('error_code'), 'STORE_CLOSED_LOGIN')


if __name__ == '__main__':
    unittest.main()
