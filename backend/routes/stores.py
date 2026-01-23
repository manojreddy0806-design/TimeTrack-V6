# backend/routes/stores.py
from flask import Blueprint, request, jsonify, g
import logging

from ..models import (
    get_stores, create_store, delete_store, get_store_by_username, update_store,
    verify_password, get_manager_by_username
)
from ..auth import require_auth, generate_token, validate_password_strength
from ..utils.request_logging import (
    get_request_id, log_request, with_request_logging, create_error_response
)

bp = Blueprint("stores", __name__)
logger = logging.getLogger(__name__)

# Rate limiter will be applied using limiter.limit() decorator after app initialization

# Blueprint-level error handler to ensure JSON responses
@bp.errorhandler(Exception)
def handle_store_error(e):
    """Handle all exceptions in stores blueprint and return JSON"""
    import traceback
    import sys
    from werkzeug.exceptions import HTTPException
    
    error_msg = str(e)
    error_type = type(e).__name__
    
    # Log the full error for debugging
    print("=" * 80)
    print(f"STORES BLUEPRINT ERROR: {error_type}: {error_msg}")
    print(f"Path: {request.path}")
    print("FULL TRACEBACK:")
    traceback.print_exc(file=sys.stdout)
    print("=" * 80)
    
    # Get status code from HTTPException if applicable
    status_code = 500
    if isinstance(e, HTTPException):
        status_code = e.code
    
    # Always return JSON error response
    import os
    if os.getenv("FLASK_ENV") == "development":
        return jsonify({
            "error": f"Error: {error_msg}",
            "error_type": error_type
        }), status_code
    else:
        return jsonify({
            "error": "An error occurred. Please try again."
        }), status_code


def _get_client_ip():
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"

@bp.get("/")
@require_auth()
@with_request_logging(lambda: f"GET {request.path}")
def list_stores():
    """
    List stores for the current tenant, optionally filtered by manager_username.
    
    Scope enforcement:
    - tenant_id is derived from token (required)
    - manager_username filter is optional query parameter
    - Returns only stores belonging to the tenant
    """
    request_id = get_request_id()
    tenant_id = g.tenant_id
    user = g.current_user
    user_id = user.get('username') or user.get('id', 'unknown')
    
    # Validate tenant_id is present (should be guaranteed by require_auth, but double-check)
    if not tenant_id:
        log_request(f"GET {request.path}", user_id, tenant_id, 401, "Missing tenant_id in token")
        return create_error_response(
            "Invalid token: missing tenant_id. Please login again.",
            401,
            request_id
        )
    
    try:
        # Get manager_username from query parameter if provided
        manager_username = request.args.get("manager_username")
        
        # Scope validation: If manager_username is provided, verify it matches the authenticated user
        # or the user has permission to view other managers' stores
        user_role = user.get('role')
        if manager_username and user_role == 'manager':
            # Managers can only view their own stores
            authenticated_username = user.get('username')
            if authenticated_username != manager_username:
                log_request(f"GET {request.path}", user_id, tenant_id, 403, 
                           f"Manager {authenticated_username} attempted to access stores for {manager_username}")
                return create_error_response(
                    "Insufficient permissions: You can only view your own stores.",
                    403,
                    request_id
                )
        
        # Fetch stores with scope enforcement
        stores = get_stores(tenant_id=tenant_id, manager_username=manager_username)
        
        # Don't return passwords in the list
        for store in stores:
            store.pop("password", None)
        
        # Log successful request
        log_request(f"GET {request.path}", user_id, tenant_id, 200)
        
        response = jsonify(stores)
        # Add request_id to response headers (not in body to maintain array structure)
        response.headers['X-Request-ID'] = request_id
        return response
        
    except Exception as e:
        # Log detailed error information
        import traceback
        error_details = {
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc(),
            'tenant_id': tenant_id,
            'manager_username': manager_username,
            'user_id': user_id
        }
        logger.error(f"Error listing stores: {error_details}", exc_info=True)
        print("=" * 80)
        print("ERROR IN LIST_STORES:")
        print(f"Error: {e}")
        print(f"Type: {type(e).__name__}")
        print(f"Tenant ID: {tenant_id}")
        print(f"Manager Username: {manager_username}")
        print("Traceback:")
        traceback.print_exc()
        print("=" * 80)
        
        log_request(f"GET {request.path}", user_id, tenant_id, 500, e)
        
        # In development, return more detailed error
        import os
        error_msg = "Failed to load stores. Please try again."
        if os.getenv("FLASK_ENV") == "development":
            error_msg = f"Failed to load stores: {str(e)}"
        
        return create_error_response(
            error_msg,
            500,
            request_id
        )

@bp.post("/")
@require_auth(roles=['manager'])
@with_request_logging(lambda: f"POST {request.path}")
def add_store():
    """
    Create a new store.
    
    Scope enforcement:
    - tenant_id is derived from token (required)
    - manager_username is derived from token (required)
    - All validation errors return structured 4xx responses
    """
    request_id = get_request_id()
    tenant_id = g.tenant_id
    user = g.current_user
    user_id = user.get('username') or user.get('id', 'unknown')
    
    # Validate tenant_id
    if not tenant_id:
        log_request(f"POST {request.path}", user_id, tenant_id, 401, "Missing tenant_id in token")
        return create_error_response(
            "Invalid token: missing tenant_id. Please login again.",
            401,
            request_id
        )
    
    # Validate manager_username
    manager_username = user.get('username')
    if not manager_username:
        log_request(f"POST {request.path}", user_id, tenant_id, 401, "Missing username in token")
        return create_error_response(
            "Manager authentication required. Invalid token.",
            401,
            request_id
        )
    
    try:
        data = request.get_json()
        if not data:
            return create_error_response("Request body is required", 400, request_id)
        
        # Validate required fields
        name = data.get("name")
        if not name:
            return create_error_response("Store name is required", 400, request_id)
        name = name.strip()
        if len(name) > 100:
            return create_error_response("Store name is too long (max 100 characters)", 400, request_id)
        if len(name) == 0:
            return create_error_response("Store name cannot be empty", 400, request_id)
        
        username = data.get("username")
        if not username:
            return create_error_response("Username is required", 400, request_id)
        username = username.strip()
        if len(username) > 50:
            return create_error_response("Username is too long (max 50 characters)", 400, request_id)
        if len(username) == 0:
            return create_error_response("Username cannot be empty", 400, request_id)
        
        password = data.get("password")
        if not password:
            return create_error_response("Password is required", 400, request_id)
        if len(password) > 200:
            return create_error_response("Password is too long (max 200 characters)", 400, request_id)
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            return create_error_response(error_msg, 400, request_id)
        
        total_boxes = data.get("total_boxes")
        if total_boxes is None:
            return create_error_response("Total boxes is required", 400, request_id)
        
        # Validate total_boxes is a positive integer
        try:
            total_boxes = int(total_boxes)
            if total_boxes < 1:
                return create_error_response("Total boxes must be a positive integer", 400, request_id)
        except (ValueError, TypeError):
            return create_error_response("Total boxes must be a positive integer", 400, request_id)
        
        # Get opening_time and closing_time (optional, format: "HH:MM" in 24-hour format)
        opening_time = data.get("opening_time")
        closing_time = data.get("closing_time")
        timezone = data.get("timezone")
        
        # Validate time format if provided (24-hour format: HH:MM, 00:00-23:59)
        import re
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
        if opening_time and opening_time.strip():
            opening_time = opening_time.strip()
            if not time_pattern.match(opening_time):
                return create_error_response(
                    "Opening time must be in 24-hour format (HH:MM), e.g., '09:00' or '17:30'",
                    400,
                    request_id
                )
        else:
            opening_time = None
        
        if closing_time and closing_time.strip():
            closing_time = closing_time.strip()
            if not time_pattern.match(closing_time):
                return create_error_response(
                    "Closing time must be in 24-hour format (HH:MM), e.g., '09:00' or '17:30'",
                    400,
                    request_id
                )
        else:
            closing_time = None
        
        # Validate timezone if provided
        if timezone and timezone.strip():
            try:
                import pytz
                pytz.timezone(timezone.strip())  # Validate timezone
                timezone = timezone.strip()
            except pytz.exceptions.UnknownTimeZoneError:
                return create_error_response(
                    f"Invalid timezone: {timezone}. Use IANA timezone names (e.g., 'America/New_York', 'UTC')",
                    400,
                    request_id
                )
        else:
            timezone = None
        
        # Create store with scope enforcement
        client_ip = _get_client_ip()
        try:
            store_id = create_store(
                tenant_id=tenant_id,
                name=name,
                username=username,
                password=password,
                total_boxes=total_boxes,
                manager_username=manager_username,
                allowed_ip=client_ip,
                opening_time=opening_time,
                closing_time=closing_time,
                timezone=timezone
            )
        except ValueError as e:
            # Handle validation errors (duplicate store name, etc.)
            log_request(f"POST {request.path}", user_id, tenant_id, 400, e)
            return create_error_response(str(e), 400, request_id)
        except Exception as e:
            # Handle database/other errors
            logger.error(f"Error creating store: {e}", exc_info=True)
            log_request(f"POST {request.path}", user_id, tenant_id, 500, e)
            return create_error_response(
                "Failed to create store. Please try again.",
                500,
                request_id
            )
        
        # Return store info without password
        store_info = {
            "id": store_id,
            "name": name,
            "username": username,
            "total_boxes": total_boxes,
            "allowed_ip": client_ip,
            "opening_time": opening_time,
            "closing_time": closing_time,
            "timezone": timezone,
            "request_id": request_id
        }
        
        # Log successful creation
        log_request(f"POST {request.path}", user_id, tenant_id, 201)
        
        response = jsonify(store_info)
        response.headers['X-Request-ID'] = request_id
        return response, 201
        
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in add_store: {e}", exc_info=True)
        log_request(f"POST {request.path}", user_id, tenant_id, 500, e)
        return create_error_response(
            "An unexpected error occurred. Please try again.",
            500,
            request_id
        )
        # Log the error for debugging
        import traceback
        import os
        error_msg = str(e)
        error_type = type(e).__name__
        traceback.print_exc()
        
        # Check if store was actually created despite the error
        # Wrap in try-except to prevent cascading errors
        try:
            from backend.models import get_store_by_name
            from backend.database import db
            
            # Rollback any pending transaction first to clear the session
            db.session.rollback()
            
            # Only check if name and tenant_id are available
            if 'name' in locals() and 'tenant_id' in locals():
                # Create a new session context to check if store exists
                # This avoids the PendingRollbackError
                existing_store = None
                try:
                    # Query the store directly with a fresh session state
                    from backend.models import Store
                    existing_store = Store.query.filter_by(
                        tenant_id=tenant_id,
                        name=name
                    ).first()
                except Exception as query_error:
                    print(f"Warning: Failed to query store: {query_error}")
                
                if existing_store:
                    # Store was created successfully, return success even if something else failed
                    store_info = {
                        "id": str(existing_store.id),
                        "name": existing_store.name,
                        "username": existing_store.username,
                        "total_boxes": existing_store.total_boxes,
                        "allowed_ip": existing_store.allowed_ip or (client_ip if 'client_ip' in locals() else None)
                    }
                    return jsonify(store_info), 201
        except Exception as check_error:
            # If checking for existing store fails, log it but continue with error response
            print(f"Warning: Failed to check if store exists: {check_error}")
            # Make sure to rollback to clear any pending state
            try:
                from backend.database import db
                db.session.rollback()
            except:
                pass
        
        # Store doesn't exist or check failed, rollback and return error
        try:
            from backend.database import db
            db.session.rollback()
        except:
            pass  # Ignore rollback errors
        
        # Return JSON error response
        if os.getenv("FLASK_ENV") == "development":
            return jsonify({
                "error": f"Failed to create store: {error_msg}",
                "error_type": error_type
            }), 500
        else:
            return jsonify({"error": "Failed to create store. Please try again."}), 500

@bp.post("/login")
def store_login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    # Try to find store (tenant_id will be extracted from store record)
    store = get_store_by_username(username)
    if not store:
        return jsonify({"error": "Invalid credentials"}), 401

    stored_password = store.get("password")
    if not stored_password or not verify_password(password, stored_password):
        return jsonify({"error": "Invalid credentials"}), 401

    allowed_ip = store.get("allowed_ip")
    client_ip = _get_client_ip()
    if allowed_ip and client_ip != allowed_ip:
        return jsonify({
            "error": "Access denied from this location.",
            "details": f"This store can only be accessed from IP {allowed_ip}. You are coming from {client_ip}."
        }), 403

    tenant_id = store.get("tenant_id")
    if not tenant_id:
        return jsonify({"error": "Store configuration error"}), 500

    # Enforce store-hours access policy (root fix)
    from backend.utils.store_access_policy import StoreAccessPolicy
    from backend.models import Store as StoreModel
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get store object to access timezone
    store_obj = StoreModel.query.filter_by(tenant_id=tenant_id, username=username).first()
    if store_obj:
        opening_time = store_obj.opening_time
        closing_time = store_obj.closing_time
        store_timezone = store_obj.timezone
        store_name = store_obj.name
        
        # Check if login is allowed
        can_login, reason, metadata = StoreAccessPolicy.can_login(
            opening_time=opening_time,
            closing_time=closing_time,
            store_timezone=store_timezone
        )
        
        # Structured logging for observability
        log_data = {
            'event': 'store_login_attempt',
            'store_id': store_name,
            'store_username': username,
            'tenant_id': tenant_id,
            'opening_time': opening_time,
            'closing_time': closing_time,
            'store_timezone': store_timezone or 'UTC',
            'allowed': can_login,
            'client_ip': client_ip
        }
        
        if metadata:
            log_data.update({
                'current_time': metadata.get('current_time'),
                'window_start': metadata.get('window_start'),
                'window_end': metadata.get('window_end')
            })
        
        if can_login:
            logger.info(f"Store login allowed: {log_data}")
        else:
            logger.warning(f"Store login blocked: {log_data}")
            error_response = {
                "error": reason or "Login is not allowed at this time.",
                "error_code": metadata.get("error_code", "STORE_CLOSED_LOGIN") if metadata else "STORE_CLOSED_LOGIN"
            }
            if metadata:
                error_response["metadata"] = metadata
            return jsonify(error_response), 403

    token = generate_token({
        "role": "store",
        "tenant_id": tenant_id,
        "storeId": store.get("name"),
        "storeName": store.get("name"),
        "username": username
    })

    store.pop("password", None)
    response_data = {**store, "token": token}
    return jsonify(response_data), 200

@bp.put("/")
@require_auth(roles=['manager'])
def edit_store():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        name = data.get("name")
        if not name:
            return jsonify({"error": "Store name is required"}), 400
        
        new_name = data.get("new_name")
        username = data.get("username")
        password = data.get("password")
        total_boxes = data.get("total_boxes")
        raw_use_current_ip = data.get("use_current_ip")
        use_current_ip = str(raw_use_current_ip).lower() in ("1", "true", "yes", "on")
        allowed_ip = data.get("allowed_ip") if "allowed_ip" in data else None
        opening_time = data.get("opening_time")
        closing_time = data.get("closing_time")
        timezone = data.get("timezone")
        
        # Validate time format if provided (24-hour format: HH:MM, 00:00-23:59)
        import re
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
        if opening_time is not None and opening_time != "" and not time_pattern.match(opening_time):
            return jsonify({"error": "Opening time must be in 24-hour format (HH:MM), e.g., '09:00' or '17:30'"}), 400
        if closing_time is not None and closing_time != "" and not time_pattern.match(closing_time):
            return jsonify({"error": "Closing time must be in 24-hour format (HH:MM), e.g., '09:00' or '17:30'"}), 400
        
        # Validate timezone if provided
        if timezone is not None and timezone != "":
            try:
                import pytz
                pytz.timezone(timezone)  # Validate timezone
            except pytz.exceptions.UnknownTimeZoneError:
                return jsonify({"error": f"Invalid timezone: {timezone}. Use IANA timezone names (e.g., 'America/New_York', 'UTC')"}), 400
        
        # Validate password strength if password is being updated
        if password:
            is_valid, error_msg = validate_password_strength(password)
            if not is_valid:
                return jsonify({"error": error_msg}), 400
        
        # Validate total_boxes if provided
        if total_boxes is not None:
            try:
                total_boxes = int(total_boxes)
                if total_boxes < 1:
                    return jsonify({"error": "Total boxes must be a positive integer"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "Total boxes must be a positive integer"}), 400
        
        ip_to_set = None
        if use_current_ip:
            ip_to_set = _get_client_ip()
        elif allowed_ip is not None:
            ip_to_set = allowed_ip or None

        tenant_id = g.tenant_id
        success = update_store(
            tenant_id=tenant_id,
            name=name,
            new_name=new_name,
            username=username,
            password=password,
            total_boxes=total_boxes,
            allowed_ip=ip_to_set,
            opening_time=opening_time if opening_time != "" else None,
            closing_time=closing_time if closing_time != "" else None,
            timezone=timezone if timezone != "" else None
        )
        if success:
            # Return updated store info
            stores = get_stores(tenant_id=tenant_id)
            updated_store = next((s for s in stores if s.get("name") == (new_name or name)), None)
            if updated_store:
                updated_store.pop("password", None)
                return jsonify(updated_store), 200
            return jsonify({"message": f"Store '{name}' updated successfully"}), 200
        else:
            return jsonify({"error": f"Store '{name}' not found or no changes made"}), 404
    except Exception as e:
        import traceback
        import os
        error_msg = str(e)
        traceback.print_exc()
        # Don't expose internal error details to client in production
        if os.getenv("FLASK_ENV") == "development":
            return jsonify({"error": f"Failed to update store: {error_msg}"}), 500
        else:
            return jsonify({"error": "Failed to update store. Please try again."}), 500

@bp.delete("/")
@require_auth(roles=['manager'])
def remove_store():
    data = request.get_json()
    name = data.get("name")
    if not name:
        return jsonify({"error": "Store name is required"}), 400
    
    tenant_id = g.tenant_id
    success = delete_store(tenant_id=tenant_id, name=name)
    if success:
        return jsonify({"message": f"Store '{name}' deleted successfully"}), 200
    else:
        return jsonify({"error": f"Store '{name}' not found"}), 404

@bp.post("/manager/login")
def manager_login():
    """Manager login endpoint"""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    # Try to find manager (we'll need tenant_id from the manager record)
    manager = get_manager_by_username(username)
    if not manager:
        return jsonify({"error": "Invalid credentials"}), 401
    
    stored_password = manager.get("password")
    if not stored_password:
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Verify password (only bcrypt hashed passwords accepted)
    if not verify_password(password, stored_password):
        return jsonify({"error": "Invalid credentials"}), 401
    
    tenant_id = manager.get("tenant_id")
    if not tenant_id:
        return jsonify({"error": "Manager configuration error"}), 500
    
    # Check tenant status
    from ..models import Tenant
    tenant = Tenant.query.get(tenant_id)
    if tenant and tenant.status != 'active':
        return jsonify({"error": f"Account is {tenant.status}. Please contact support."}), 403
    
    # Determine role
    if manager.get("is_super_admin"):
        role = "super-admin"
    elif manager.get("is_admin"):
        role = "admin"
        regions = manager.get("regions", [])
    else:
        role = "manager"
    
    # Generate JWT token
    token_data = {
        "role": role,
        "tenant_id": tenant_id,
        "name": manager.get("name", "Manager"),
        "username": username,
        "is_super_admin": manager.get("is_super_admin", False),
        "is_admin": manager.get("is_admin", False)
    }
    
    if role == "admin":
        token_data["regions"] = regions
    
    token = generate_token(token_data)
    
    # Don't return password
    manager.pop("password", None)
    response_data = {
        "role": role,
        "tenant_id": tenant_id,
        "name": manager.get("name", "Manager"),
        "username": username,
        "token": token
    }
    
    if role == "admin":
        response_data["regions"] = regions
    
    return jsonify(response_data), 200


