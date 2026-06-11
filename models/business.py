import uuid
from datetime import datetime
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("models")

def get_current_date_str():
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

def get_current_datetime_str():
    """Returns the current date and time in YYYY-MM-DD HH:MM:SS format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def update_expired_statuses():
    """Checks all active subscriptions and marks them as Expired if the current date and time is past their expiration date/time."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = get_current_datetime_str()
    try:
        # Select all Active business subscriptions that have expired
        cursor.execute(
            "SELECT id, name FROM businesses WHERE status = 'Active' AND expiration_date < ? AND expiration_date IS NOT NULL AND expiration_date != ''",
            (now_str,)
        )
        expired_businesses = cursor.fetchall()
        
        if expired_businesses:
            for b in expired_businesses:
                logger.info(f"Subscription for business '{b['name']}' (ID: {b['id']}) has expired.")
                
            cursor.execute(
                "UPDATE businesses SET status = 'Expired' WHERE status = 'Active' AND expiration_date < ? AND expiration_date IS NOT NULL AND expiration_date != ''",
                (now_str,)
            )
            conn.commit()
            logger.info(f"Updated status to 'Expired' for {len(expired_businesses)} businesses.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error checking and updating expired statuses: {e}")
    finally:
        conn.close()

def add_business(name, review_url, address="", contact_info="", logo_path="", qr_mode="Dynamic", subscription_duration="12 months", expiration_date=None, status="Active"):
    """Adds a new business record to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    qr_identifier = str(uuid.uuid4())[:8] # Short unique slug
    
    # If no expiration date provided and duration is set, calculate it
    if not expiration_date:
        expiration_date = calculate_expiration_date(subscription_duration)

    try:
        cursor.execute("""
        INSERT INTO businesses (name, review_url, address, contact_info, logo_path, qr_identifier, subscription_duration, expiration_date, status, qr_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, review_url, address, contact_info, logo_path, qr_identifier, subscription_duration, expiration_date, status, qr_mode))
        
        conn.commit()
        business_id = cursor.lastrowid
        logger.info(f"Business '{name}' added successfully with ID {business_id} and Identifier {qr_identifier}")
        return business_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding business '{name}': {e}")
        raise e
    finally:
        conn.close()

def update_business(business_id, name, review_url, address, contact_info, logo_path, qr_mode, subscription_duration, expiration_date, status):
    """Updates an existing business record in the database."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        UPDATE businesses
        SET name = ?, review_url = ?, address = ?, contact_info = ?, logo_path = ?, qr_mode = ?, subscription_duration = ?, expiration_date = ?, status = ?
        WHERE id = ?
        """, (name, review_url, address, contact_info, logo_path, qr_mode, subscription_duration, expiration_date, status, business_id))
        
        conn.commit()
        logger.info(f"Business ID {business_id} updated successfully.")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating business ID {business_id}: {e}")
        raise e
    finally:
        conn.close()

def delete_business(business_id):
    """Deletes a business record from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM businesses WHERE id = ?", (business_id,))
        conn.commit()
        logger.info(f"Business ID {business_id} deleted successfully.")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting business ID {business_id}: {e}")
        raise e
    finally:
        conn.close()

def get_business(business_id):
    """Retrieves a single business record by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM businesses WHERE id = ?", (business_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching business ID {business_id}: {e}")
        return None
    finally:
        conn.close()

def get_business_by_identifier(qr_identifier):
    """Retrieves a single business record by its unique QR identifier."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM businesses WHERE qr_identifier = ?", (qr_identifier,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching business by identifier {qr_identifier}: {e}")
        return None
    finally:
        conn.close()

def get_settings():
    """Retrieves all global settings from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        return {row['key']: row['value'] for row in rows}
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        return {}
    finally:
        conn.close()

def save_setting(key, value):
    """Saves or updates a setting in the settings table."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        logger.info(f"Setting '{key}' set to '{value}'")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving setting '{key}': {e}")
        return False
    finally:
        conn.close()

def list_businesses(search_query=None, status_filter=None):
    """Lists businesses with optional filters for name/address search and status."""
    update_expired_statuses() # Always keep status clean when listing
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM businesses"
    params = []
    conditions = []
    
    if search_query:
        conditions.append("(name LIKE ? OR address LIKE ? OR contact_info LIKE ?)")
        like_query = f"%{search_query}%"
        params.extend([like_query, like_query, like_query])
        
    if status_filter and status_filter != "All":
        conditions.append("status = ?")
        params.append(status_filter)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY id DESC"
    
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error listing businesses: {e}")
        return []
    finally:
        conn.close()

def get_dashboard_stats():
    """Gathers dashboard metrics including total businesses, active, expired, and expiring soon."""
    update_expired_statuses()
    
    conn = get_connection()
    cursor = conn.cursor()
    today = get_current_date_str()
    
    # Get expiring soon window from settings (default 30 days)
    settings = get_settings()
    expiring_soon_days = int(settings.get("expiring_soon_days", 30))
    
    try:
        cursor.execute("SELECT COUNT(*) FROM businesses")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM businesses WHERE status = 'Active'")
        active = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM businesses WHERE status = 'Expired'")
        expired = cursor.fetchone()[0]
        
        # Calculate expiring soon count
        cursor.execute("""
            SELECT COUNT(*) FROM businesses 
            WHERE status = 'Active' 
            AND substr(expiration_date, 1, 10) >= ? 
            AND substr(expiration_date, 1, 10) <= date(?, '+' || ? || ' days')
            AND expiration_date IS NOT NULL AND expiration_date != ''
        """, (today, today, expiring_soon_days))
        expiring_soon = cursor.fetchone()[0]
        
        # Fetch up to 5 soon-to-expire businesses for dashboard alert table
        cursor.execute("""
            SELECT * FROM businesses 
            WHERE status = 'Active' 
            AND substr(expiration_date, 1, 10) >= ?
            AND substr(expiration_date, 1, 10) <= date(?, '+' || ? || ' days')
            AND expiration_date IS NOT NULL AND expiration_date != ''
            ORDER BY expiration_date ASC LIMIT 5
        """, (today, today, expiring_soon_days))
        expiring_list = [dict(row) for row in cursor.fetchall()]
        
        return {
            "total": total,
            "active": active,
            "expired": expired,
            "expiring_soon": expiring_soon,
            "expiring_list": expiring_list
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {"total": 0, "active": 0, "expired": 0, "expiring_soon": 0, "expiring_list": []}
    finally:
        conn.close()
 
def calculate_expiration_date(duration_str):
    """Calculates expiration date from a duration string (e.g. '1 month', '12 months')."""
    from datetime import timedelta
    # Basic relative delta calculation
    # Supports "1 month", "3 months", "6 months", "12 months", "No expiration"
    # Custom dates are passed directly and will bypass this function or be parsed
    now = datetime.now()
    if duration_str == "1 month":
        res = now + timedelta(days=30)
    elif duration_str == "3 months":
        res = now + timedelta(days=90)
    elif duration_str == "6 months":
        res = now + timedelta(days=180)
    elif duration_str == "12 months":
        res = now + timedelta(days=365)
    else:
        return "" # No expiration date or custom handled manually
        
    return res.strftime("%Y-%m-%d 23:59:59")
