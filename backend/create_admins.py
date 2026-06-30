import sys
from app.core.database import get_db_connection
from app.routes.auth_routes import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admins_to_create = [
    {"username": "admin1", "password": "admin1_password", "role": "Admin"},
    {"username": "admin2", "password": "admin2_password", "role": "Admin"},
    {"username": "admin3", "password": "admin3_password", "role": "Admin"}
]

def create_admins():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for admin in admins_to_create:
                pwd_hash = hash_password(admin["password"])
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO NOTHING;
                    """,
                    (admin["username"], pwd_hash, admin["role"])
                )
                logger.info(f"Admin user '{admin['username']}' processed.")
            conn.commit()
            logger.info("Admin users created successfully.")
    except Exception as e:
        logger.error(f"Error creating admin users: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_admins()
