"""
Migration script to add timezone column to stores table and clock_out_type column to timeclock table.
This enables store-hours access control with timezone support.
"""
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from backend.app import create_app
from backend.database import db
from sqlalchemy import text

def migrate():
    """Add timezone column to stores table and clock_out_type column to timeclock table"""
    app = create_app()
    with app.app_context():
        try:
            # Check if stores table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'stores'
                );
            """))
            stores_table_exists = result.scalar()
            
            if not stores_table_exists:
                print("⚠ stores table does not exist. Skipping timezone column addition.")
            else:
                # Check if timezone column already exists
                result = db.session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'stores' 
                        AND column_name = 'timezone'
                    );
                """))
                timezone_exists = result.scalar()
                
                if not timezone_exists:
                    # Add timezone column
                    print("Adding timezone column to stores table...")
                    db.session.execute(text("""
                        ALTER TABLE stores 
                        ADD COLUMN timezone VARCHAR(100);
                    """))
                    print("✓ timezone column added to stores table")
                else:
                    print("✓ timezone column already exists in stores table")
            
            # Check if timeclock table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'timeclock'
                );
            """))
            timeclock_table_exists = result.scalar()
            
            if not timeclock_table_exists:
                print("⚠ timeclock table does not exist. Skipping clock_out_type column addition.")
            else:
                # Check if clock_out_type column already exists
                result = db.session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'timeclock' 
                        AND column_name = 'clock_out_type'
                    );
                """))
                clock_out_type_exists = result.scalar()
                
                if not clock_out_type_exists:
                    # Add clock_out_type column
                    print("Adding clock_out_type column to timeclock table...")
                    db.session.execute(text("""
                        ALTER TABLE timeclock 
                        ADD COLUMN clock_out_type VARCHAR(20);
                    """))
                    print("✓ clock_out_type column added to timeclock table")
                else:
                    print("✓ clock_out_type column already exists in timeclock table")
            
            db.session.commit()
            print("✓ Migration complete: timezone and clock_out_type columns added successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate()
