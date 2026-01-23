"""
Request Logging and Observability Utilities

Provides request ID generation, logging, and error tracking for API routes.
"""

import uuid
import logging
import traceback
from functools import wraps
from flask import request, g, jsonify
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

def generate_request_id():
    """Generate a unique request ID"""
    return str(uuid.uuid4())


def get_request_id():
    """Get request ID from Flask g object or generate new one"""
    if not hasattr(g, 'request_id'):
        g.request_id = generate_request_id()
    return g.request_id


def log_request(route_name, user_id=None, tenant_id=None, status_code=200, error=None):
    """
    Log API request with observability data
    
    Args:
        route_name: Name of the route (e.g., 'GET /stores/')
        user_id: User ID from token
        tenant_id: Tenant ID from token
        status_code: HTTP status code
        error: Error object or message if request failed
    """
    request_id = get_request_id()
    
    # Use ET time for logging timestamps
    from backend.utils.timezone_utils import now_et
    
    log_data = {
        'request_id': request_id,
        'route': route_name,
        'method': request.method,
        'path': request.path,
        'status_code': status_code,
        'timestamp': now_et().isoformat(),
        'user_id': user_id,
        'tenant_id': tenant_id,
        'ip_address': request.remote_addr
    }
    
    if error:
        log_data['error'] = str(error)
        log_data['error_type'] = type(error).__name__
        if isinstance(error, Exception):
            log_data['error_traceback'] = traceback.format_exc()
    
    # Log based on status code
    if status_code >= 500:
        logger.error(f"API Request Failed: {log_data}")
    elif status_code >= 400:
        logger.warning(f"API Request Error: {log_data}")
    else:
        logger.info(f"API Request: {log_data}")
    
    return request_id


def with_request_logging(route_name_func=None):
    """
    Decorator to add request logging to a route
    
    Usage:
        @with_request_logging(lambda: f"{request.method} {request.path}")
        def my_route():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate request ID
            g.request_id = generate_request_id()
            
            # Get route name
            if route_name_func:
                route_name = route_name_func()
            else:
                route_name = f"{request.method} {request.path}"
            
            # Extract user info from g (set by require_auth)
            user_id = None
            tenant_id = None
            if hasattr(g, 'current_user'):
                user_id = g.current_user.get('username') or g.current_user.get('id')
            if hasattr(g, 'tenant_id'):
                tenant_id = g.tenant_id
            
            try:
                # Execute route
                result = f(*args, **kwargs)
                
                # Extract status code from result
                status_code = 200
                if isinstance(result, tuple):
                    status_code = result[1] if len(result) > 1 else 200
                
                # Log successful request
                log_request(route_name, user_id, tenant_id, status_code)
                
                # Add request_id to response if it's JSON
                if isinstance(result, tuple) and len(result) > 0:
                    response_data = result[0]
                    if hasattr(response_data, 'get_json'):
                        # It's a Flask Response object
                        try:
                            json_data = response_data.get_json()
                            if json_data and isinstance(json_data, dict):
                                json_data['request_id'] = g.request_id
                                from flask import jsonify
                                return jsonify(json_data), status_code
                        except:
                            pass
                    elif isinstance(response_data, dict):
                        response_data['request_id'] = g.request_id
                        return jsonify(response_data), status_code
                
                return result
            except Exception as e:
                # Log error
                status_code = 500
                if hasattr(e, 'code'):
                    status_code = e.code
                
                log_request(route_name, user_id, tenant_id, status_code, error=e)
                
                # Re-raise to let error handler deal with it
                raise
        return decorated_function
    return decorator


def create_error_response(error, status_code=500, request_id=None):
    """
    Create a normalized error response
    
    Args:
        error: Error message or exception
        status_code: HTTP status code
        request_id: Request ID for tracking
    
    Returns:
        Flask JSON response
    """
    if request_id is None:
        request_id = get_request_id()
    
    error_message = str(error) if error else 'An error occurred'
    error_code = 'UNKNOWN_ERROR'
    
    # Map status codes to error codes
    if status_code == 401:
        error_code = 'UNAUTHORIZED'
    elif status_code == 403:
        error_code = 'FORBIDDEN'
    elif status_code == 404:
        error_code = 'NOT_FOUND'
    elif status_code == 400:
        error_code = 'BAD_REQUEST'
    elif status_code == 422:
        error_code = 'VALIDATION_ERROR'
    elif status_code >= 500:
        error_code = 'SERVER_ERROR'
    
    response = {
        'error': error_message,
        'error_code': error_code,
        'request_id': request_id,
        'status_code': status_code
    }
    
    # Add stack trace in development
    import os
    if os.getenv('FLASK_ENV') == 'development' and isinstance(error, Exception):
        response['traceback'] = traceback.format_exc()
    
    return jsonify(response), status_code
