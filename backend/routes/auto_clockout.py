# backend/routes/auto_clockout.py
"""
Auto clock-out endpoint to clock out employees who forgot to clock out
30 minutes after store closing time (root fix).

This endpoint should be called periodically (e.g., via cron job or scheduled task).
Uses the centralized StoreAccessPolicy module for authoritative business rules.
"""
from flask import Blueprint, jsonify, g, request
from datetime import datetime, timedelta, timezone as dt_timezone
from backend.database import db
from backend.models import Store, TimeClock
from backend.auth import require_auth
from backend.utils.store_access_policy import StoreAccessPolicy
from backend.utils.timezone_utils import now_et, today_start_utc_naive, et_to_utc_naive

bp = Blueprint("auto_clockout", __name__)


@bp.post("/auto-clockout")
@require_auth(roles=['manager', 'admin', 'super-admin'])
def auto_clockout():
    """
    Auto clock out employees who forgot to clock out 30 minutes after closing time.
    This endpoint should be called periodically (e.g., via cron job or scheduled task).
    
    Uses the centralized StoreAccessPolicy module for authoritative business rules.
    """
    try:
        tenant_id = g.tenant_id
        # Get current time in ET for business logic
        now_et_time = now_et()
        # Use UTC naive for database queries
        today_start = today_start_utc_naive()
        
        # Get all stores for this tenant
        stores = Store.query.filter_by(tenant_id=tenant_id).all()
        
        auto_clocked_out = []
        
        for store in stores:
            if not store.closing_time:
                continue
            
            try:
                # Use policy module to get auto clock-out time (returns ET timezone-aware)
                auto_clockout_dt = StoreAccessPolicy.auto_clock_out_at(
                    closing_time=store.closing_time,
                    store_timezone=store.timezone,
                    reference_time=now_et_time
                )
                
                if not auto_clockout_dt:
                    continue
                
                # Ensure auto_clockout_dt is in ET (should already be from policy)
                if auto_clockout_dt.tzinfo is None:
                    from backend.utils.timezone_utils import get_app_timezone
                    auto_clockout_et = get_app_timezone().localize(auto_clockout_dt)
                else:
                    from backend.utils.timezone_utils import get_app_timezone
                    auto_clockout_et = auto_clockout_dt.astimezone(get_app_timezone())
                
                # Convert to UTC naive for database storage
                auto_clockout_naive = et_to_utc_naive(auto_clockout_et)
                
                # Only auto clock out if current time (ET) is past the auto clock-out time (ET)
                if now_et_time >= auto_clockout_et:
                    # Find all employees clocked in today at this store who haven't clocked out
                    # and haven't been auto clocked out already
                    active_entries = TimeClock.query.filter(
                        TimeClock.tenant_id == tenant_id,
                        TimeClock.store_id == store.name,
                        TimeClock.clock_in >= today_start,
                        TimeClock.clock_out == None
                    ).all()
                    
                    for entry in active_entries:
                        # Idempotency check: don't double-close
                        if entry.clock_out is not None:
                            continue
                        
                        # Auto clock out at the policy-defined time
                        clock_in_time = entry.clock_in
                        hours_worked = (auto_clockout_naive - clock_in_time).total_seconds() / 3600
                        
                        entry.clock_out = auto_clockout_naive
                        entry.clock_out_type = "AUTO"
                        entry.hours_worked = round(hours_worked, 2)
                        
                        auto_clocked_out.append({
                            "employee_id": str(entry.employee_id),
                            "employee_name": entry.employee_name,
                            "store_id": store.name,
                            "clock_in_time": clock_in_time.isoformat(),
                            "clock_out_time": auto_clockout_naive.isoformat(),
                            "hours_worked": round(hours_worked, 2),
                            "auto_clockout_time": auto_clockout_dt.strftime('%H:%M') if auto_clockout_dt else None
                        })
            except (ValueError, AttributeError) as e:
                # Skip stores with invalid closing time format
                print(f"Warning: Skipping auto-clockout for store {store.name}: {e}")
                continue
        
        if auto_clocked_out:
            db.session.commit()
            return jsonify({
                "success": True,
                "auto_clocked_out_count": len(auto_clocked_out),
                "auto_clocked_out": auto_clocked_out
            }), 200
        else:
            return jsonify({
                "success": True,
                "auto_clocked_out_count": 0,
                "message": "No employees needed auto clock-out"
            }), 200
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.post("/auto-clockout/all-tenants")
def auto_clockout_all_tenants():
    """
    Auto clock-out endpoint for all tenants (for system-wide cron job).
    This endpoint should be called periodically (e.g., every 5 minutes).
    
    Note: This endpoint does NOT require authentication as it's meant to be called
    by a system cron job. In production, you should secure this with an API key
    or restrict access by IP.
    """
    try:
        from backend.models import Tenant
        
        # Get all active tenants
        tenants = Tenant.query.filter_by(status='active').all()
        
        total_auto_clocked_out = []
        
        for tenant in tenants:
            tenant_id = tenant.id
            # Get current time in ET for business logic
            now_et_time = now_et()
            # Use UTC naive for database queries
            today_start = today_start_utc_naive()
            
            # Get all stores for this tenant
            stores = Store.query.filter_by(tenant_id=tenant_id).all()
            
            for store in stores:
                if not store.closing_time:
                    continue
                
                try:
                    # Use policy module to get auto clock-out time (returns ET timezone-aware)
                    auto_clockout_dt = StoreAccessPolicy.auto_clock_out_at(
                        closing_time=store.closing_time,
                        store_timezone=store.timezone,
                        reference_time=now_et_time
                    )
                    
                    if not auto_clockout_dt:
                        continue
                    
                    # Ensure auto_clockout_dt is in ET (should already be from policy)
                    if auto_clockout_dt.tzinfo is None:
                        from backend.utils.timezone_utils import get_app_timezone
                        auto_clockout_et = get_app_timezone().localize(auto_clockout_dt)
                    else:
                        from backend.utils.timezone_utils import get_app_timezone
                        auto_clockout_et = auto_clockout_dt.astimezone(get_app_timezone())
                    
                    # Convert to UTC naive for database storage
                    auto_clockout_naive = et_to_utc_naive(auto_clockout_et)
                    
                    # Only auto clock out if current time (ET) is past the auto clock-out time (ET)
                    # Check within a 5-minute window to handle cron job timing
                    time_diff_et = (now_et_time - auto_clockout_et).total_seconds() / 60
                    if 0 <= time_diff_et <= 5:  # Within 5 minutes after auto clock-out time
                        # Find all employees clocked in today at this store who haven't clocked out
                        active_entries = TimeClock.query.filter(
                            TimeClock.tenant_id == tenant_id,
                            TimeClock.store_id == store.name,
                            TimeClock.clock_in >= today_start,
                            TimeClock.clock_out == None
                        ).all()
                        
                        for entry in active_entries:
                            # Idempotency check: don't double-close
                            if entry.clock_out is not None:
                                continue
                            
                            # Auto clock out at the policy-defined time
                            clock_in_time = entry.clock_in
                            hours_worked = (auto_clockout_naive - clock_in_time).total_seconds() / 3600
                            
                            entry.clock_out = auto_clockout_naive
                            entry.clock_out_type = "AUTO"
                            entry.hours_worked = round(hours_worked, 2)
                            
                            total_auto_clocked_out.append({
                                "tenant_id": tenant_id,
                                "employee_id": str(entry.employee_id),
                                "employee_name": entry.employee_name,
                                "store_id": store.name,
                                "clock_in_time": clock_in_time.isoformat(),
                                "clock_out_time": auto_clockout_naive.isoformat(),
                                "hours_worked": round(hours_worked, 2)
                            })
                except (ValueError, AttributeError) as e:
                    # Skip stores with invalid closing time format
                    print(f"Warning: Skipping auto-clockout for store {store.name} (tenant {tenant_id}): {e}")
                    continue
        
        if total_auto_clocked_out:
            db.session.commit()
            return jsonify({
                "success": True,
                "auto_clocked_out_count": len(total_auto_clocked_out),
                "auto_clocked_out": total_auto_clocked_out
            }), 200
        else:
            return jsonify({
                "success": True,
                "auto_clocked_out_count": 0,
                "message": "No employees needed auto clock-out"
            }), 200
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
