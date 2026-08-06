"""
/// <summary>
/// Automated test and verification file for system security and configurations (Security & Hardening Tests)
/// </summary>
"""

import sys
import os
import hashlib
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add the project path so the app package can be detected
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from app.main import app
from app.core.config import settings
from app.routes.auth_routes import hash_password, PASSWORD_SALT

client = TestClient(app)

def test_password_hashing():
    print("1. Testing PBKDF2 Password Hashing...")
    p_hash = hash_password("testpassword123")
    assert len(p_hash) == 64
    assert p_hash != hashlib.sha256(("testpassword123" + "arionex_secure_salt_2026").encode('utf-8')).hexdigest()
    print("-> Test 1 (PBKDF2 Password Hashing): PASSED")

def test_legacy_password_migration():
    print("\n2. Testing Legacy Password Hashing Auto-Migration during Login...")
    legacy_salt = "arionex_secure_salt_2026"
    legacy_pwd_hash = hashlib.sha256(("mypassword123" + legacy_salt).encode('utf-8')).hexdigest()
    
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # First fetchone call to verify username and role
    mock_cursor.fetchone.side_effect = [
        (legacy_pwd_hash, "Analyst"),
    ]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    with patch("app.routes.auth_routes.get_db_connection", return_value=mock_conn):
        response = client.post("/v1/auth/login", json={
            "username": "legacy_user",
            "password": "mypassword123"
        })
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["user"]["username"] == "legacy_user"
        
        # Verify UPDATE query was executed
        executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
        assert any("UPDATE users SET password_hash" in q for q in executed_queries)
        print("-> Test 2 (Legacy Password Migration): PASSED")

def test_cors_configuration():
    print("\n3. Testing CORS Origins restriction...")
    from app.main import ALLOWED_ORIGINS
    
    assert isinstance(ALLOWED_ORIGINS, list)
    assert len(ALLOWED_ORIGINS) > 0
    
    for origin in ALLOWED_ORIGINS:
        assert origin.startswith("http://") or origin.startswith("https://")
        
    print("-> Test 3 (CORS Allowed Origins): PASSED")

def test_health_checks():
    print("\n4. Testing Health Check Dependency Endpoints...")
    
    mock_db_conn = MagicMock()
    mock_db_cursor = MagicMock()
    mock_db_cursor.fetchone.return_value = (1,)
    mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor
    
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    
    mock_minio = MagicMock()
    mock_minio.client.list_buckets.return_value = []
    mock_minio.is_fallback = False
    
    with patch("app.core.database.get_db_connection", return_value=mock_db_conn), \
         patch("redis.Redis.from_url", return_value=mock_redis), \
         patch("app.core.minio_client.storage_manager", mock_minio):
        
        # Test 1: Liveness check
        response = client.get("/health/liveness")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"
        
        # Test 2: Readiness check
        response = client.get("/health/readiness")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
        
        # Test 3: Detailed health check
        response = client.get("/health")
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "healthy"
        assert res_data["checks"]["postgres"] == "healthy"
        assert res_data["checks"]["redis"] == "healthy"
        assert res_data["checks"]["minio"]["status"] == "healthy"
        
    # Test 4: Database Down readiness check
    with patch("app.core.database.get_db_connection", side_effect=Exception("Database Connection Error")), \
         patch("redis.Redis.from_url", return_value=mock_redis), \
         patch("app.core.minio_client.storage_manager", mock_minio):
        
        response = client.get("/health/readiness")
        assert response.status_code == 503
        
        response = client.get("/health")
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "unhealthy"
        assert res_data["checks"]["postgres"] == "unhealthy"
        
    print("-> Test 4 (Dependency Health Checks): PASSED")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING SECURITY & HARDENING TESTS")
    print("=========================================")
    try:
        test_password_hashing()
        test_legacy_password_migration()
        test_cors_configuration()
        test_health_checks()
        print("=========================================")
        print("ALL SECURITY & HARDENING TESTS PASSED!")
        print("=========================================")
        sys.exit(0)
    except AssertionError as ae:
        print(f"[ERROR] TEST SUITE FAILED: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] UNEXPECTED ERROR: {str(e)}")
        sys.exit(1)
