# backend/app.py
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import click
import sys
import os
from pathlib import Path

# If this module is executed directly (python backend/app.py), the
# import system will set sys.path[0] to the `backend/` directory which
# prevents importing the `backend` package using absolute imports
# like `backend.config`. Insert the project root into sys.path when
# running as a script so absolute imports work.
if __package__ is None:
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from backend.config import Config
from backend.database import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Disable Flask's default HTML error pages - we'll handle errors ourselves
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['DEBUG'] = False  # Disable debug mode HTML error pages
    CORS(app)

    db.init_app(app)
    
    # Import models here to register them with SQLAlchemy before creating tables
    # This must happen after db.init_app() but before db.create_all()
    from backend import models
    
    # Create all database tables
    # For serverless functions, we should allow the app to start even if DB is unavailable
    # The database connection will be attempted on first use
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages for common issues
            if "could not translate host name" in error_msg or "No such host is known" in error_msg:
                print("\n" + "="*80)
                print("DATABASE CONNECTION WARNING: Hostname cannot be resolved")
                print("="*80)
                print(f"Error: {error_msg}")
                print("\nThis usually means:")
                print("1. The DATABASE_URL hostname is incomplete or incorrect")
                print("2. For Render.com: Make sure the hostname includes the full domain")
                print("   Example: dpg-xxxxx-xxxxx-a.oregon-postgres.render.com")
                print("   NOT: dpg-xxxxx-xxxxx-a")
                print("3. Check your .env file or environment variables")
                print("4. Verify the database is running and accessible")
                print("\nNOTE: App will continue to start. Database will be connected on first use.")
                print("="*80 + "\n")
            elif "SSL connection" in error_msg:
                print("\n" + "="*80)
                print("DATABASE SSL CONNECTION WARNING")
                print("="*80)
                print(f"Error: {error_msg}")
                print("\nThis usually means:")
                print("1. The database requires SSL but the connection failed")
                print("2. Check your DATABASE_URL includes sslmode=require")
                print("3. For Render.com: SSL is required")
                print("\nNOTE: App will continue to start. Database will be connected on first use.")
                print("="*80 + "\n")
            else:
                print(f"\nWARNING: Database connection failed: {error_msg}")
                print("NOTE: App will continue to start. Database will be connected on first use.\n")
            # Don't re-raise - allow app to start and handle DB errors at request time
            # This is important for serverless functions where DB might not be available at cold start
    
    # Initialize rate limiter
    # Don't apply default limits globally - only apply to specific routes that need protection
    # This prevents static files and favicon from being rate limited
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=None,  # No global limits - apply limits only to specific routes
        storage_uri="memory://",  # Use in-memory storage (use Redis in production)
        headers_enabled=True,
        swallow_errors=True  # Don't crash on rate limit errors, just return 429
    )
    # Make limiter available globally for blueprints
    app.extensions['limiter'] = limiter

    from backend.routes.employees import bp as employees_bp
    from backend.routes.timeclock import bp as timeclock_bp
    from backend.routes.inventory import bp as inventory_bp
    from backend.routes.eod import bp as eod_bp
    from backend.routes.stores import bp as stores_bp
    from backend.routes.face import bp as face_bp
    from backend.routes.inventory_history import bp as inventory_history_bp
    from backend.routes.managers import bp as managers_bp
    from backend.routes.tenants import bp as tenants_bp

    # Register error handlers BEFORE blueprints to ensure they catch all errors
    # Global error handler to ensure all API errors return JSON
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all unhandled exceptions and return JSON for API routes"""
        from flask import request
        import traceback
        import sys
        from werkzeug.exceptions import HTTPException
        
        # Check if this is an API request
        if request.path.startswith('/api/'):
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Log the full error for debugging
            print("=" * 80)
            print(f"UNHANDLED EXCEPTION: {error_type}: {error_msg}")
            print(f"Path: {request.path}")
            print("FULL TRACEBACK:")
            traceback.print_exc(file=sys.stdout)
            print("=" * 80)
            
            # Get status code from HTTPException if applicable
            status_code = 500
            if isinstance(e, HTTPException):
                status_code = e.code
            
            # Return JSON error response
            import os
            if os.getenv("FLASK_ENV") == "development":
                response = jsonify({
                    "error": f"Internal server error: {error_msg}",
                    "error_type": error_type
                })
            else:
                response = jsonify({
                    "error": "Internal server error. Please try again."
                })
            
            response.status_code = status_code
            return response
        
        # For non-API routes, let Flask handle it
        raise
    
    # Register blueprints - order matters! More specific routes first
    app.register_blueprint(tenants_bp, url_prefix="/api/tenants")
    app.register_blueprint(inventory_history_bp, url_prefix="/api/inventory/history")
    app.register_blueprint(employees_bp, url_prefix="/api/employees")
    app.register_blueprint(timeclock_bp, url_prefix="/api/timeclock")
    app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
    app.register_blueprint(eod_bp, url_prefix="/api/eod")
    app.register_blueprint(stores_bp, url_prefix="/api/stores")
    app.register_blueprint(face_bp, url_prefix="/api/face")
    app.register_blueprint(managers_bp, url_prefix="/api/managers")
    
    # Apply rate limiting to login endpoints
    # Flask-Limiter will automatically apply rate limits based on decorators
    try:
        limiter.limit("5 per minute")(stores_bp.view_functions['store_login'])
        limiter.limit("5 per minute")(stores_bp.view_functions['manager_login'])
        limiter.limit("5 per minute")(managers_bp.view_functions['super_admin_login'])
    except (KeyError, AttributeError):
        # Endpoints not found or limiter not available - this is okay during development
        pass

    # Ensure API routes always return JSON, even for error responses
    @app.after_request
    def ensure_json_for_api(response):
        """Ensure API routes return JSON content type, convert HTML errors to JSON"""
        from flask import request
        if request.path.startswith('/api/'):
            # Get response data to check if it's HTML
            response_data = response.get_data(as_text=True)
            
            # Check if response is HTML (starts with <!doctype or <html)
            is_html = False
            if response_data and (response_data.strip().lower().startswith('<!doctype') or 
                                 response_data.strip().lower().startswith('<html') or
                                 (response.content_type and 'text/html' in response.content_type)):
                is_html = True
            
            # If response is HTML (error page), convert to JSON
            if is_html and response.status_code >= 400:
                import os
                error_msg = "Internal server error. Please try again."
                if os.getenv("FLASK_ENV") == "development":
                    # Try to extract error message from HTML
                    if 'Exception:' in response_data or 'Error:' in response_data:
                        # Extract first error line
                        lines = response_data.split('\n')
                        for line in lines:
                            if 'Exception:' in line or 'Error:' in line:
                                error_msg = line.strip()[:200]
                                break
                    else:
                        error_msg = f"HTML error page received. Check server logs for details."
                json_response = jsonify({"error": error_msg})
                json_response.status_code = response.status_code
                return json_response
            
            # Ensure content-type is application/json for API error responses
            if response.status_code >= 400:
                response.content_type = 'application/json'
        return response
    
    # Ensure exceptions are propagated (already set above, but being explicit)
    # This ensures our error handlers catch exceptions before Flask's default handlers
    
    @app.get("/api/health")
    def health():
        return {"status": "ok"}
    
    # Serve favicon to prevent 404 errors
    @app.get("/favicon.ico")
    def favicon():
        return "", 204  # No Content - prevents 404 but doesn't serve a file
    
    # Debug routes removed for production security
    # To enable debug routes, only do so in development environment
    import os
    if os.getenv("FLASK_ENV") == "development":
        @app.get("/api/debug/routes")
        def debug_routes():
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append({
                    "endpoint": rule.endpoint,
                    "methods": list(rule.methods),
                    "rule": str(rule)
                })
            return jsonify({"routes": routes})

    # Project root path - handle both local and serverless environments
    # In serverless (Vercel), files are in /var/task/, so we need to find the project root
    _current_file = Path(__file__).resolve()
    
    # Try to find project root by looking for common markers
    project_root = None
    possible_roots = [
        _current_file.parent.parent,  # Standard: backend/app.py -> root
        Path("/var/task"),  # Vercel serverless
        Path.cwd(),  # Current working directory
    ]
    
    # Also try walking up from current file
    test_path = _current_file.parent
    for _ in range(5):  # Max 5 levels up
        if (test_path / "backend" / "app.py").exists() or (test_path / "api" / "index.py").exists():
            possible_roots.append(test_path)
            break
        test_path = test_path.parent
    
    # Find the first valid project root
    for root in possible_roots:
        if root.exists():
            # Check if this looks like the project root
            if (root / "backend" / "app.py").exists() or (root / "api" / "index.py").exists():
                project_root = root
                break
    
    # Fallback to standard resolution if nothing found
    if project_root is None:
        project_root = _current_file.parent.parent
    
    frontend_pages = project_root / "frontend" / "pages"
    frontend_static = project_root / "frontend" / "static"
    
    # Use a mutable container for landing_dist so it can be updated if found at alternative path
    landing_dist_container = {"path": project_root / "landing" / "dist" / "public"}
    
    # Debug: Log the resolved paths
    print(f"DEBUG: Resolved paths - project_root: {project_root}")
    print(f"DEBUG: frontend_pages exists: {frontend_pages.exists()}")
    print(f"DEBUG: frontend_static exists: {frontend_static.exists()}")
    print(f"DEBUG: landing_dist: {landing_dist_container['path']}")
    
    # Helper function to check if landing page exists (check dynamically)
    def landing_page_exists():
        landing_dist = landing_dist_container["path"]
        exists = landing_dist.exists() and (landing_dist / "index.html").exists()
        if not exists:
            # Debug logging for serverless environments
            print(f"DEBUG: Landing page check - landing_dist: {landing_dist}")
            print(f"DEBUG: Landing dist exists: {landing_dist.exists()}")
            if landing_dist.exists():
                print(f"DEBUG: Landing dist contents: {list(landing_dist.iterdir()) if landing_dist.is_dir() else 'not a directory'}")
                index_file = landing_dist / "index.html"
                print(f"DEBUG: index.html exists: {index_file.exists()}")
            else:
                # Try alternative paths
                alt_paths = [
                    project_root / "landing" / "dist" / "public",
                    Path("/var/task/landing/dist/public"),
                    Path("/var/task") / "landing" / "dist" / "public",
                    Path.cwd() / "landing" / "dist" / "public",
                ]
                for alt_path in alt_paths:
                    if alt_path.exists() and (alt_path / "index.html").exists():
                        print(f"DEBUG: Found landing dist at alternative path: {alt_path}")
                        # Update the container so future calls use the correct path
                        landing_dist_container["path"] = alt_path
                        return True
        return exists
    
    # Get the actual landing_dist path for use in routes
    def get_landing_dist():
        return landing_dist_container["path"]

    # Serve login page at /login.html FIRST (before landing page)
    # This ensures login.html is served before React SPA can intercept
    @app.get("/login.html")
    def serve_login_html():
        return send_from_directory(frontend_pages, "login.html")
    
    # Serve login page at /login
    @app.get("/login")
    def serve_login():
        return send_from_directory(frontend_pages, "login.html")
    
    # Serve HTML pages from frontend/pages
    @app.get("/<path:page>.html")
    def serve_page(page):
        return send_from_directory(frontend_pages, f"{page}.html")
    
    # Serve landing page at root (if available, otherwise serve login)
    @app.get("/")
    def serve_landing():
        if landing_page_exists():
            return send_from_directory(get_landing_dist(), "index.html")
        else:
            # Fallback to login page if landing page doesn't exist
            return send_from_directory(frontend_pages, "login.html")
    
    # Keep index.html for backward compatibility (redirect to login)
    @app.get("/index.html")
    def serve_index():
        return send_from_directory(frontend_pages, "login.html")
    
    # Serve signup page as root signup route
    @app.get("/signup")
    def serve_signup():
        return send_from_directory(frontend_pages, "signup.html")
    
    @app.get("/signup-success")
    def serve_signup_success():
        return send_from_directory(frontend_pages, "signup-success.html")

    # Serve static CSS files
    @app.get("/static/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(frontend_static / "css", filename)

    # Serve static JS files
    @app.get("/static/js/<path:filename>")
    def serve_js(filename):
        js_file = frontend_static / "js" / filename
        if not js_file.exists():
            print(f"DEBUG: JS file not found - {js_file}")
            print(f"DEBUG: frontend_static: {frontend_static}")
            print(f"DEBUG: frontend_static exists: {frontend_static.exists()}")
            if frontend_static.exists():
                print(f"DEBUG: frontend_static contents: {list(frontend_static.iterdir()) if frontend_static.is_dir() else 'not a directory'}")
        return send_from_directory(frontend_static / "js", filename)
    
    # Serve landing page static assets (images, etc.) - only if landing exists
    @app.get("/assets/<path:filename>")
    def serve_landing_assets(filename):
        if landing_page_exists():
            return send_from_directory(get_landing_dist() / "assets", filename)
        from flask import abort
        abort(404)
    
    # Serve landing page public assets (images in public folder)
    @app.get("/<path:filename>")
    def serve_landing_public(filename):
        # Don't interfere with API routes
        if filename.startswith('api/'):
            from flask import abort
            abort(404)
        
        # Check if it's a landing page asset (images like hero-bg.jpg, etc.)
        if landing_page_exists():
            landing_dist = get_landing_dist()
            landing_public_file = landing_dist / filename
            if landing_public_file.exists() and landing_public_file.is_file():
                return send_from_directory(landing_dist, filename)
        
        # Try frontend/pages for explicit HTML files (legacy pages like login.html, signup.html)
        if filename.endswith('.html'):
            return send_from_directory(frontend_pages, filename)
        
        # Try static folders
        if filename.startswith('static/'):
            return send_from_directory(frontend_static, filename[7:])  # Remove 'static/' prefix
        
        # Fallback to SPA index.html for client-side routed paths (e.g., /contact)
        # Only if landing page exists, otherwise return 404
        if landing_page_exists():
            return send_from_directory(get_landing_dist(), "index.html")
        from flask import abort
        abort(404)


    # CLI command to seed default stores
    @app.cli.command("seed-stores")
    def seed_stores_command():
        from backend.models import Store, add_default_inventory_to_store, hash_password
        stores_count = Store.query.count()
        if stores_count == 0:
            store1 = Store(
                name="Lawrence",
                username="lawrence",
                password=hash_password("lawrence123"),
                total_boxes=0,
                manager_username=None
            )
            store2 = Store(
                name="Oakville",
                username="oakville",
                password=hash_password("oakville123"),
                total_boxes=0,
                manager_username=None
            )
            db.session.add(store1)
            db.session.add(store2)
            db.session.commit()
            
            # Get tenant_id (assuming first tenant or default tenant)
            from backend.models import Tenant
            tenant = Tenant.query.first()
            tenant_id = tenant.id if tenant else None
            
            if tenant_id:
                # Add default inventory items for each store
                count1 = add_default_inventory_to_store(tenant_id=tenant_id, store_name="Lawrence")
                count2 = add_default_inventory_to_store(tenant_id=tenant_id, store_name="Oakville")
                click.echo(f"✓ Seeded default stores with inventory:")
                click.echo(f"  - Lawrence: {count1} items")
                click.echo(f"  - Oakville: {count2} items")
            else:
                click.echo("Warning: No tenant found, skipping inventory creation")
                click.echo("✓ Seeded default stores (no inventory added)")
        else:
            click.echo("Stores already exist; skipping seed")
    
    # CLI command to add default inventory to existing stores
    @app.cli.command("add-inventory")
    @click.argument("store_name")
    def add_inventory_command(store_name):
        """Add default inventory items to a specific store"""
        from backend.models import Store, add_default_inventory_to_store
        
        store = Store.query.filter_by(name=store_name).first()
        if not store:
            click.echo(f"❌ Error: Store '{store_name}' not found")
            click.echo("\nAvailable stores:")
            for s in Store.query.all():
                click.echo(f"  - {s.name}")
            return
        
        count = add_default_inventory_to_store(tenant_id=store.tenant_id, store_name=store_name)
        click.echo(f"✓ Added {count} new inventory items to store '{store_name}'")
        
        # Show total inventory count
        from backend.models import Inventory
        total = Inventory.query.filter_by(store_id=store_name).count()
        click.echo(f"  Total inventory items: {total}")
    
    # CLI command to run database migrations
    @app.cli.command("migrate")
    def migrate_command():
        """Run database migrations"""
        from backend.migrations.add_device_type_to_inventory import migrate
        migrate()
    
    # CLI command to add default inventory to existing stores
    @app.cli.command("add-inventory-to-stores")
    def add_inventory_to_stores_command():
        """Add default inventory to all existing stores that don't have inventory"""
        from backend.migrations.add_default_inventory_to_existing_stores import migrate
        migrate()
    
    # CLI command to show inventory count for all stores
    @app.cli.command("check-inventory")
    def check_inventory_command():
        """Show inventory item count for all stores"""
        from backend.models import Store, Inventory
        
        stores = Store.query.all()
        if not stores:
            click.echo("No stores found")
            return
        
        click.echo("\n📦 Inventory Status:")
        click.echo("-" * 40)
        for store in stores:
            count = Inventory.query.filter_by(store_id=store.name).count()
            click.echo(f"{store.name:20} {count:3} items")
        click.echo("-" * 40)

    return app

if __name__ == "__main__":
    app = create_app()
    # Only run in debug mode if explicitly set in environment
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode)

