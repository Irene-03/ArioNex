"""
/// <summary>
/// Automated test file for the ArioNex refresh token mechanism (ArioNex Refresh Token Logic Verification Script)
/// </summary>
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add the project path so the app package can be detected
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.routes.auth_routes import create_session_token, verify_session_token, hash_password

class TestRefreshTokenLogic(unittest.TestCase):
    
    def test_token_helpers(self):
        print("Testing create and verify token helpers...")
        payload = {"username": "test_user", "role": "Analyst"}
        
        # Test access token
        access_token = create_session_token(payload, expires_in=10, token_type="access")
        verified_access = verify_session_token(access_token, expected_type="access")
        self.assertIsNotNone(verified_access)
        self.assertEqual(verified_access["username"], "test_user")
        self.assertEqual(verified_access["type"], "access")
        
        # Test refresh token
        refresh_token = create_session_token(payload, expires_in=100, token_type="refresh")
        verified_refresh = verify_session_token(refresh_token, expected_type="refresh")
        self.assertIsNotNone(verified_refresh)
        self.assertEqual(verified_refresh["username"], "test_user")
        self.assertEqual(verified_refresh["type"], "refresh")
        
        # Test rejection of a wrong token type
        self.assertIsNone(verify_session_token(access_token, expected_type="refresh"))
        self.assertIsNone(verify_session_token(refresh_token, expected_type="access"))
        print(" Token helpers checks PASSED.\n")

    @patch("app.routes.auth_routes.get_db_connection")
    def test_login_and_refresh_endpoints(self, mock_get_db):
        print("Testing login and refresh API endpoints...")
        
        # Mock database results
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        pwd_hash = hash_password("admin123")
        mock_cur.fetchone.return_value = (pwd_hash, "Admin")
        
        client = TestClient(app)
        
        # 1. Test the login endpoint
        login_res = client.post("/v1/auth/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.json()
        
        self.assertIn("access_token", login_data)
        self.assertIn("refresh_token", login_data)
        self.assertEqual(login_data["token_type"], "bearer")
        self.assertEqual(login_data["user"]["username"], "admin")
        self.assertEqual(login_data["user"]["role"], "Admin")
        
        print("  Login endpoint checks PASSED.")
        
        # 2. Test the refresh endpoint
        refresh_payload = {"refresh_token": login_data["refresh_token"]}
        refresh_res = client.post("/v1/auth/refresh", json=refresh_payload)
        self.assertEqual(refresh_res.status_code, 200)
        refresh_data = refresh_res.json()
        
        self.assertIn("access_token", refresh_data)
        self.assertIn("refresh_token", refresh_data)
        self.assertEqual(refresh_data["token_type"], "bearer")
        
        # Verify the correctness of the new access token
        new_payload = verify_session_token(refresh_data["access_token"], expected_type="access")
        self.assertIsNotNone(new_payload)
        self.assertEqual(new_payload["username"], "admin")
        self.assertEqual(new_payload["role"], "Admin")
        
        # 3. Test sending an invalid refresh token
        invalid_res = client.post("/v1/auth/refresh", json={"refresh_token": "invalid_token_format"})
        self.assertEqual(invalid_res.status_code, 401)
        
        print("  Refresh endpoint checks PASSED.\n")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING REFRESH TOKEN AUTOMATED TESTS")
    print("=========================================")
    unittest.main()
