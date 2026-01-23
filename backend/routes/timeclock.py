# backend/routes/timeclock.py
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from backend.database import db
from backend.models import Employee, TimeClock
from backend.auth import require_auth
from backend.services.face_service import (
    find_best_match,
    validate_face_descriptor,
    compress_image,
    euclidean_distance
)
from backend.utils.timezone_utils import now_et, now_utc_naive, today_start_utc_naive, et_to_utc_naive

bp = Blueprint("timeclock", __name__)


@bp.post("/clock-in")
@require_auth()
def clock_in_route():
    """Legacy clock-in endpoint (kept for compatibility)"""
    data = request.get_json()
    employee_id = data.get("employee_id")
    store_id = data.get("store_id")  # Optional store_id for policy check
    tenant_id = g.tenant_id
    
    # Verify employee belongs to this tenant
    employee = Employee.query.filter_by(id=int(employee_id), tenant_id=tenant_id).first()
    if not employee:
        return jsonify({"error": "Employee not found"}), 404
    
    # Enforce store-hours access policy (root fix)
    if store_id or employee.store_id:
        from backend.utils.store_access_policy import StoreAccessPolicy
        from backend.models import Store
        
        effective_store_id = store_id or employee.store_id
        store = Store.query.filter_by(tenant_id=tenant_id, name=effective_store_id).first()
        
        if store and store.opening_time and store.closing_time:
            can_clock, reason, metadata = StoreAccessPolicy.can_clock_action(
                opening_time=store.opening_time,
                closing_time=store.closing_time,
                store_timezone=store.timezone
            )
            
            if not can_clock:
                error_response = {
                    "error": reason or "Clock-in is not allowed at this time.",
                    "error_code": metadata.get("error_code", "OUTSIDE_CLOCK_WINDOW") if metadata else "OUTSIDE_CLOCK_WINDOW"
                }
                if metadata:
                    error_response["metadata"] = metadata
                return jsonify(error_response), 403
    
    # Get current time in ET, convert to UTC naive for database storage
    clock_in_et = now_et()
    clock_in_utc_naive = et_to_utc_naive(clock_in_et)
    
    entry = TimeClock(
        tenant_id=tenant_id,
        employee_id=int(employee_id),
        store_id=store_id or employee.store_id,
        clock_in=clock_in_utc_naive,
        clock_out=None
    )
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({"entry_id": str(entry.id)}), 201


@bp.post("/clock-out")
@require_auth()
def clock_out_route():
    """Legacy clock-out endpoint (kept for compatibility)"""
    data = request.get_json()
    entry_id = data.get("entry_id")
    tenant_id = g.tenant_id
    
    try:
        entry = TimeClock.query.filter_by(id=int(entry_id), tenant_id=tenant_id).first()
        if not entry:
            return jsonify({"error": "Invalid or already clocked out entry"}), 400
        
        if entry.clock_out:
            return jsonify({"error": "Entry already clocked out"}), 400
        
        # Enforce store-hours access policy (root fix)
        if entry.store_id:
            from backend.utils.store_access_policy import StoreAccessPolicy
            from backend.models import Store
            
            store = Store.query.filter_by(tenant_id=tenant_id, name=entry.store_id).first()
            
            if store and store.opening_time and store.closing_time:
                can_clock, reason, metadata = StoreAccessPolicy.can_clock_action(
                    opening_time=store.opening_time,
                    closing_time=store.closing_time,
                    store_timezone=store.timezone
                )
                
                if not can_clock:
                    error_response = {
                        "error": reason or "Clock-out is not allowed at this time.",
                        "error_code": metadata.get("error_code", "OUTSIDE_CLOCK_WINDOW") if metadata else "OUTSIDE_CLOCK_WINDOW"
                    }
                    if metadata:
                        error_response["metadata"] = metadata
                    return jsonify(error_response), 403
        
        # Get current time in ET, convert to UTC naive for database storage
        clock_out_et = now_et()
        clock_out_utc_naive = et_to_utc_naive(clock_out_et)
        
        entry.clock_out = clock_out_utc_naive
        entry.clock_out_type = "MANUAL"
        db.session.commit()
        return jsonify({"ok": True})
    except:
        return jsonify({"error": "Invalid entry_id format"}), 400


@bp.post("/clock-in-face")
@require_auth()
def clock_in_face():
    """
    Clock in using face recognition.
    
    Request JSON:
    {
        "face_descriptor": [0.123, -0.456, ...],
        "face_image": "data:image/jpeg;base64,...",
        "store_id": "Lawrence"
    }
    """
    try:
        data = request.get_json()
        tenant_id = g.tenant_id
        
        face_descriptor = data.get("face_descriptor")
        face_image = data.get("face_image")
        store_id = data.get("store_id")
        
        if not face_descriptor:
            return jsonify({"error": "face_descriptor is required"}), 400
        
        # Validate face descriptor
        if not validate_face_descriptor(face_descriptor):
            return jsonify({"error": "Invalid face descriptor format"}), 400
        
        # Get all employees with registered faces for this tenant
        registered_employees = Employee.query.filter_by(tenant_id=tenant_id, face_registered=True).all()
        
        if not registered_employees:
            return jsonify({
                "success": False,
                "error": "No employees with registered faces found. Please register your face first."
            }), 404
        
        # Convert to dict format for find_best_match
        employee_dicts = []
        for emp in registered_employees:
            emp_dict = emp.to_dict()
            emp_dict['_id'] = emp.id
            employee_dicts.append(emp_dict)
        
        # Find best match
        match = find_best_match(face_descriptor, employee_dicts, threshold=0.6)
        
        # Minimum confidence threshold (30%) - reject low-confidence matches
        MIN_CONFIDENCE = 0.3
        
        if not match or match.get("confidence", 0) < MIN_CONFIDENCE:
            error_msg = "Face not recognized. "
            if match and match.get("confidence", 0) < MIN_CONFIDENCE:
                error_msg += f"Confidence too low ({match.get('confidence', 0)*100:.1f}%). "
            error_msg += "Please contact your manager to register or update your face."
            return jsonify({
                "success": False,
                "error": error_msg
            }), 404
        
        employee_id = int(match["employee_id"])
        employee_name = match["employee_name"]
        confidence = match["confidence"]
        # Convert numpy types to Python float for database compatibility
        confidence = float(confidence) if confidence is not None else None
        
        # Get employee object (verify tenant_id)
        employee = Employee.query.filter_by(id=employee_id, tenant_id=tenant_id).first()
        
        if not employee:
            return jsonify({"error": "Employee not found or does not belong to this tenant"}), 404
        
        if employee:
            # Get existing descriptors
            existing_descriptors = employee.get_face_descriptors()
            if not existing_descriptors and employee.get_face_descriptor():
                existing_descriptors = [employee.get_face_descriptor()]
            
            # Check if this new face is different enough from existing ones
            min_distance = float('inf')
            for existing_desc in existing_descriptors:
                distance = euclidean_distance(face_descriptor, existing_desc)
                if distance < min_distance:
                    min_distance = distance
            
            # If distance > 0.3, it's a different appearance - add it to learn
            if min_distance > 0.3 and confidence > 0.7:
                existing_descriptors.append(face_descriptor)
                # Limit to last 5 registrations
                if len(existing_descriptors) > 5:
                    existing_descriptors = existing_descriptors[-5:]
                
                employee.set_face_descriptors(existing_descriptors)
                db.session.commit()
        
        # Check if employee is already clocked in today (using UTC naive for database query)
        today_start = today_start_utc_naive()
        
        existing_entry = TimeClock.query.filter(
            TimeClock.tenant_id == tenant_id,
            TimeClock.employee_id == employee_id,
            TimeClock.clock_in >= today_start,
            TimeClock.clock_out == None
        ).first()
        
        if existing_entry:
            clock_in_iso = existing_entry.clock_in.isoformat()
            if not clock_in_iso.endswith('Z') and existing_entry.clock_in.tzinfo is None:
                clock_in_iso += 'Z'
            
            return jsonify({
                "success": False,
                "error": f"{employee_name} is already clocked in today.",
                "employee_name": employee_name,
                "clock_in_time": clock_in_iso
            }), 400
        
        # Enforce store-hours access policy (root fix)
        if store_id:
            from backend.utils.store_access_policy import StoreAccessPolicy
            from backend.models import Store
            
            store = Store.query.filter_by(tenant_id=tenant_id, name=store_id).first()
            
            if store and store.opening_time and store.closing_time:
                can_clock, reason, metadata = StoreAccessPolicy.can_clock_action(
                    opening_time=store.opening_time,
                    closing_time=store.closing_time,
                    store_timezone=store.timezone
                )
                
                if not can_clock:
                    error_response = {
                        "success": False,
                        "error": reason or "Clock-in is not allowed at this time.",
                        "error_code": metadata.get("error_code", "OUTSIDE_CLOCK_WINDOW") if metadata else "OUTSIDE_CLOCK_WINDOW"
                    }
                    if metadata:
                        error_response["metadata"] = metadata
                    return jsonify(error_response), 403
        
        # Compress face image
        compressed_image = compress_image(face_image, max_size=400) if face_image else None
        
        # Track storage usage for face image
        if compressed_image:
            from backend.utils.storage import calculate_base64_size, check_storage_limit, update_storage_usage
            
            image_size = calculate_base64_size(compressed_image)
            
            # Check storage limit
            has_space, error_msg = check_storage_limit(tenant_id, image_size)
            if not has_space:
                return jsonify({"error": error_msg}), 400
            
            # Update storage usage
            update_storage_usage(tenant_id, image_size)
        
        # Create clock-in entry (ET time converted to UTC naive for storage)
        clock_in_et = now_et()
        clock_in_time = et_to_utc_naive(clock_in_et)
        entry = TimeClock(
            tenant_id=tenant_id,
            employee_id=employee_id,
            employee_name=employee_name,
            store_id=store_id,
            clock_in=clock_in_time,
            clock_out=None,
            clock_in_face_image=compressed_image,
            clock_in_confidence=confidence
        )
        
        db.session.add(entry)
        db.session.commit()
        
        # Check if employee clocked in late (after opening time) and create alert
        # Use ET time for comparison with store hours
        if store_id:
            from backend.models import Store, create_alert
            try:
                store = Store.query.filter_by(tenant_id=tenant_id, name=store_id).first()
                if store and store.opening_time and store.manager_username:
                    try:
                        # Compare in ET timezone
                        opening_hour, opening_minute = map(int, store.opening_time.split(':'))
                        opening_time_today_et = clock_in_et.replace(hour=opening_hour, minute=opening_minute, second=0, microsecond=0)
                        
                        # Check if clock-in is after opening time (in ET)
                        if clock_in_et > opening_time_today_et:
                            # Calculate how many minutes late
                            minutes_late = int((clock_in_et - opening_time_today_et).total_seconds() / 60)
                            
                            # Create alert for manager (format time in ET)
                            create_alert(
                                tenant_id=tenant_id,
                                store_id=store_id,
                                manager_username=store.manager_username,
                                alert_type='late_clock_in',
                                title=f'Late Clock-In: {employee_name}',
                                message=f'{employee_name} clocked in {minutes_late} minute{"s" if minutes_late != 1 else ""} late at {clock_in_et.strftime("%H:%M")} ET. Store opening time is {store.opening_time} ET.',
                                employee_id=employee_id,
                                employee_name=employee_name
                            )
                    except (ValueError, AttributeError) as e:
                        # If time parsing fails, skip alert creation
                        print(f"Warning: Could not create late clock-in alert: {e}")
            except Exception as e:
                # Don't fail clock-in if alert creation fails
                print(f"Warning: Error creating alert: {e}")
        
        clock_in_iso = entry.clock_in.isoformat()
        if not clock_in_iso.endswith('Z') and entry.clock_in.tzinfo is None:
            clock_in_iso += 'Z'
        
        return jsonify({
            "success": True,
            "entry_id": str(entry.id),
            "employee_id": str(employee_id),
            "employee_name": employee_name,
            "clock_in_time": clock_in_iso,
            "confidence": confidence
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.post("/clock-out-face")
@require_auth()
def clock_out_face():
    """
    Clock out using face recognition.
    
    Request JSON:
    {
        "face_descriptor": [0.123, -0.456, ...],
        "face_image": "data:image/jpeg;base64,...",
        "store_id": "Lawrence"
    }
    """
    try:
        data = request.get_json()
        tenant_id = g.tenant_id
        
        face_descriptor = data.get("face_descriptor")
        face_image = data.get("face_image")
        store_id = data.get("store_id")
        
        if not face_descriptor:
            return jsonify({"error": "face_descriptor is required"}), 400
        
        # Validate face descriptor
        if not validate_face_descriptor(face_descriptor):
            return jsonify({"error": "Invalid face descriptor format"}), 400
        
        # Get all employees with registered faces for this tenant
        registered_employees = Employee.query.filter_by(tenant_id=tenant_id, face_registered=True).all()
        
        if not registered_employees:
            return jsonify({
                "success": False,
                "error": "No employees with registered faces found."
            }), 404
        
        # Convert to dict format for find_best_match
        employee_dicts = []
        for emp in registered_employees:
            emp_dict = emp.to_dict()
            emp_dict['_id'] = emp.id
            employee_dicts.append(emp_dict)
        
        # Find best match
        match = find_best_match(face_descriptor, employee_dicts, threshold=0.6)
        
        if not match:
            return jsonify({
                "success": False,
                "error": "Face not recognized. Please try again or contact your manager."
            }), 404
        
        employee_id = int(match["employee_id"])
        employee_name = match["employee_name"]
        confidence = match["confidence"]
        # Convert numpy types to Python float for database compatibility
        confidence = float(confidence) if confidence is not None else None
        
        # Get employee object (verify tenant_id)
        employee = Employee.query.filter_by(id=employee_id, tenant_id=tenant_id).first()
        
        if not employee:
            return jsonify({"error": "Employee not found or does not belong to this tenant"}), 404
        
        if employee:
            # Get existing descriptors
            existing_descriptors = employee.get_face_descriptors()
            if not existing_descriptors and employee.get_face_descriptor():
                existing_descriptors = [employee.get_face_descriptor()]
            
            # Check if this new face is different enough from existing ones
            min_distance = float('inf')
            for existing_desc in existing_descriptors:
                distance = euclidean_distance(face_descriptor, existing_desc)
                if distance < min_distance:
                    min_distance = distance
            
            # If distance > 0.3, it's a different appearance - add it to learn
            if min_distance > 0.3 and confidence > 0.7:
                existing_descriptors.append(face_descriptor)
                # Limit to last 5 registrations
                if len(existing_descriptors) > 5:
                    existing_descriptors = existing_descriptors[-5:]
                
                employee.set_face_descriptors(existing_descriptors)
                db.session.commit()
        
        # Find active clock-in entry for today (using UTC naive for database query)
        today_start = today_start_utc_naive()
        
        active_entry = TimeClock.query.filter(
            TimeClock.tenant_id == tenant_id,
            TimeClock.employee_id == employee_id,
            TimeClock.clock_in >= today_start,
            TimeClock.clock_out == None
        ).first()
        
        if not active_entry:
            return jsonify({
                "success": False,
                "error": f"{employee_name} is not clocked in today. Please clock in first.",
                "employee_name": employee_name
            }), 400
        
        # Enforce store-hours access policy (root fix)
        if store_id:
            from backend.utils.store_access_policy import StoreAccessPolicy
            from backend.models import Store
            
            store = Store.query.filter_by(tenant_id=tenant_id, name=store_id).first()
            
            if store and store.opening_time and store.closing_time:
                # Check if clock-out is allowed
                can_clock, reason, metadata = StoreAccessPolicy.can_clock_action(
                    opening_time=store.opening_time,
                    closing_time=store.closing_time,
                    store_timezone=store.timezone
                )
                
                if not can_clock:
                    # Check if we should auto clock-out instead
                    auto_clockout_time = StoreAccessPolicy.auto_clock_out_at(
                        closing_time=store.closing_time,
                        store_timezone=store.timezone
                    )
                    
                    if auto_clockout_time:
                        # Get current time in ET
                        now_et_time = now_et()
                        
                        # Convert auto_clockout_time to ET if needed (it should already be in store timezone/ET)
                        if auto_clockout_time.tzinfo is None:
                            # If naive, assume it's in store timezone (ET)
                            from backend.utils.timezone_utils import get_app_timezone
                            auto_clockout_et = get_app_timezone().localize(auto_clockout_time)
                        else:
                            # Convert to ET
                            from backend.utils.timezone_utils import get_app_timezone
                            auto_clockout_et = auto_clockout_time.astimezone(get_app_timezone())
                        
                        # If it's past auto clock-out time, auto clock out
                        if now_et_time >= auto_clockout_et:
                            # Convert to UTC naive for database storage
                            clock_out_time = et_to_utc_naive(auto_clockout_et)
                            clock_in_time = active_entry.clock_in
                            hours_worked = (clock_out_time - clock_in_time).total_seconds() / 3600
                            
                            active_entry.clock_out = clock_out_time
                            active_entry.clock_out_type = "AUTO"
                            active_entry.hours_worked = round(hours_worked, 2)
                            db.session.commit()
                            
                            clock_in_iso = clock_in_time.isoformat()
                            if not clock_in_iso.endswith('Z') and clock_in_time.tzinfo is None:
                                clock_in_iso += 'Z'
                            
                            clock_out_iso = clock_out_time.isoformat()
                            if not clock_out_iso.endswith('Z') and clock_out_time.tzinfo is None:
                                clock_out_iso += 'Z'
                            
                            return jsonify({
                                "success": True,
                                "auto_clockout": True,
                                "entry_id": str(active_entry.id),
                                "employee_id": str(employee_id),
                                "employee_name": employee_name,
                                "clock_in_time": clock_in_iso,
                                "clock_out_time": clock_out_iso,
                                "hours_worked": round(hours_worked, 2),
                                "message": f"Auto clocked out at {auto_clockout_et.strftime('%H:%M')} ET (30 minutes after closing time {store.closing_time} ET)"
                            }), 200
                    
                    # Not past auto clock-out time, deny manual clock-out
                    error_response = {
                        "success": False,
                        "error": reason or "Clock-out is not allowed at this time.",
                        "error_code": metadata.get("error_code", "OUTSIDE_CLOCK_WINDOW") if metadata else "OUTSIDE_CLOCK_WINDOW"
                    }
                    if metadata:
                        error_response["metadata"] = metadata
                    return jsonify(error_response), 403
        
        # Compress face image
        compressed_image = compress_image(face_image, max_size=400) if face_image else None
        
        # Track storage usage for face image
        if compressed_image:
            from backend.utils.storage import calculate_base64_size, check_storage_limit, update_storage_usage
            
            old_image_size = calculate_base64_size(active_entry.clock_out_face_image) if active_entry.clock_out_face_image else 0
            new_image_size = calculate_base64_size(compressed_image)
            size_change = new_image_size - old_image_size
            
            # Check storage limit
            if size_change > 0:
                has_space, error_msg = check_storage_limit(tenant_id, size_change)
                if not has_space:
                    return jsonify({"error": error_msg}), 400
            
            # Update storage usage
            if size_change != 0:
                update_storage_usage(tenant_id, size_change)
        
        # Update entry with clock-out time (ET time converted to UTC naive for storage)
        clock_out_et = now_et()
        clock_out_time = et_to_utc_naive(clock_out_et)
        clock_in_time = active_entry.clock_in
        hours_worked = (clock_out_time - clock_in_time).total_seconds() / 3600
        
        active_entry.clock_out = clock_out_time
        active_entry.clock_out_type = "MANUAL"
        active_entry.clock_out_face_image = compressed_image
        active_entry.clock_out_confidence = confidence
        active_entry.hours_worked = round(hours_worked, 2)
        
        db.session.commit()
        
        clock_in_iso = clock_in_time.isoformat()
        if not clock_in_iso.endswith('Z') and clock_in_time.tzinfo is None:
            clock_in_iso += 'Z'
        
        clock_out_iso = clock_out_time.isoformat()
        if not clock_out_iso.endswith('Z') and clock_out_time.tzinfo is None:
            clock_out_iso += 'Z'
        
        return jsonify({
            "success": True,
            "entry_id": str(active_entry.id),
            "employee_id": str(employee_id),
            "employee_name": employee_name,
            "clock_in_time": clock_in_iso,
            "clock_out_time": clock_out_iso,
            "hours_worked": round(hours_worked, 2),
            "confidence": confidence
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/today")
@require_auth()
def get_today_entries():
    """
    Get all timeclock entries for today for a specific store.
    
    Query params:
    - store_id: Store identifier
    """
    try:
        tenant_id = g.tenant_id
        store_id = request.args.get("store_id")
        
        if not store_id:
            return jsonify({"error": "store_id is required"}), 400
        
        today_start = today_start_utc_naive()
        tomorrow_start = today_start + timedelta(days=1)
        
        entries = TimeClock.query.filter(
            TimeClock.tenant_id == tenant_id,
            TimeClock.store_id == store_id,
            TimeClock.clock_in >= today_start,
            TimeClock.clock_in < tomorrow_start
        ).order_by(TimeClock.clock_in.desc()).all()
        
        # Format entries for response
        formatted_entries = [entry.to_dict() for entry in entries]
        
        return jsonify({
            "date": today_start.date().isoformat(),
            "store_id": store_id,
            "employees": formatted_entries,
            "total_count": len(formatted_entries)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/history")
@require_auth()
def get_history():
    """
    Get timeclock history for a store.
    
    Query params:
    - store_id: Store identifier
    - days: Number of days to look back (default 30)
    """
    try:
        tenant_id = g.tenant_id
        store_id = request.args.get("store_id")
        days = int(request.args.get("days", 30))
        
        if not store_id:
            return jsonify({"error": "store_id is required"}), 400
        
        # Use UTC naive for database queries
        start_date = now_utc_naive() - timedelta(days=days)
        
        entries = TimeClock.query.filter(
            TimeClock.tenant_id == tenant_id,
            TimeClock.store_id == store_id,
            TimeClock.clock_in >= start_date
        ).order_by(TimeClock.clock_in.desc()).all()
        
        # Format entries for response
        formatted_entries = [entry.to_dict() for entry in entries]
        
        return jsonify({
            "store_id": store_id,
            "entries": formatted_entries,
            "total_count": len(formatted_entries),
            "days": days
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/employee/<employee_id>/history")
@require_auth()
def get_employee_history(employee_id):
    """
    Get timeclock history for a specific employee.
    
    Path params:
    - employee_id: Employee identifier
    
    Query params:
    - days: Number of days to look back (default 90)
    """
    try:
        tenant_id = g.tenant_id
        days = int(request.args.get("days", 90))
        # Use UTC naive for database queries
        start_date = now_utc_naive() - timedelta(days=days)
        
        # Verify employee belongs to this tenant
        employee = Employee.query.filter_by(id=int(employee_id), tenant_id=tenant_id).first()
        if not employee:
            return jsonify({"error": "Employee not found"}), 404
        
        # Find all entries for this employee
        entries = TimeClock.query.filter(
            TimeClock.tenant_id == tenant_id,
            TimeClock.employee_id == int(employee_id),
            TimeClock.clock_in >= start_date
        ).order_by(TimeClock.clock_in.desc()).all()
        
        # Format entries for response
        formatted_entries = [entry.to_dict() for entry in entries]
        
        return jsonify({
            "employee_id": employee_id,
            "entries": formatted_entries,
            "total_count": len(formatted_entries),
            "days": days
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
