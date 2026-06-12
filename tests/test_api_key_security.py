"""
/// <summary>
/// فایل تست خودکار و راستی‌آزمایی امنیت کلیدهای API و فایل پیکربندی (API Key Security & Env Protection Tests)
/// </summary>
"""

import sys
import os
import asyncio
import hashlib
from unittest.mock import MagicMock, patch

# اضافه کردن مسیر پروژه جهت شناسایی پکیج app
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from fastapi import HTTPException
from app.helpers.auth import verify_api_key, get_current_user_or_api_key
from app.routes.config_routes import _update_env_file, update_active_configuration
from app.routes.integration_routes import create_apikey, list_apikeys, APIKeyCreate
from app.core.config import settings

# Helper database mock connection
def get_mock_db(mock_rows=None, fetchone_val=None, count=1):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    if mock_rows is not None:
        mock_cursor.fetchall.return_value = mock_rows
    if fetchone_val is not None:
        mock_cursor.fetchone.return_value = fetchone_val
    else:
        mock_cursor.fetchone.return_value = (count,)
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor

async def test_apikey_creation_and_hashing():
    print("1. Testing API Key creation and hashing...")
    
    # Mock database to return values from RETURNING clause
    # (id, name, api_key_hash, is_active, created_at)
    mock_token = "anx_live_d8f58b73f847db12c222ffda84729f1234bdf7817ab4123f"
    hashed_token = hashlib.sha256(mock_token.encode("utf-8")).hexdigest()
    
    mock_conn, mock_cursor = get_mock_db(
        fetchone_val=(101, "CRM-System", hashed_token, True, "2026-06-12 12:00:00")
    )
    
    with patch("app.routes.integration_routes.get_db_connection", return_value=mock_conn):
        payload = APIKeyCreate(name="CRM-System")
        response = await create_apikey(payload)
        
        # Verify response returns the raw, copyable token
        assert response.api_key.startswith("anx_live_"), "Created key must start with prefix"
        assert response.name == "CRM-System"
        
        # Verify the database query executed with the hashed token, NOT the raw token
        insert_query = mock_cursor.execute.call_args[0][0]
        insert_args = mock_cursor.execute.call_args[0][1]
        
        assert "INSERT INTO api_keys" in insert_query
        assert insert_args[0] == "CRM-System"
        assert insert_args[1] == hashlib.sha256(response.api_key.encode("utf-8")).hexdigest(), "Should insert hashed token"
        print("-> Test 1 (API Key Hashed Insertion): PASSED")

async def test_apikey_listing_masked():
    print("\n2. Testing API Key listing is securely masked...")
    
    # Mock database to return a hashed key
    mock_token = "anx_live_d8f58b73f847db12c222ffda84729f1234bdf7817ab4123f"
    hashed_token = hashlib.sha256(mock_token.encode("utf-8")).hexdigest()
    
    mock_conn, _ = get_mock_db(
        mock_rows=[(101, "CRM-System", hashed_token, True, "2026-06-12 12:00:00", None)]
    )
    
    with patch("app.routes.integration_routes.get_db_connection", return_value=mock_conn):
        response_list = await list_apikeys()
        
        assert len(response_list) == 1
        listed_key = response_list[0]
        
        # Verify the listed key does not contain the raw token or the full hash
        assert listed_key.api_key.startswith("anx_live_***"), "Listed key must be masked"
        assert len(listed_key.api_key) < 40, "Masked key should be short placeholder"
        assert listed_key.api_key.endswith(hashed_token[-4:]), "Masked key should contain last 4 characters of hash"
        print("-> Test 2 (API Key Listing Masking): PASSED")

async def test_verify_hashed_apikey():
    print("\n3. Testing request verification using hashed API key...")
    
    mock_token = "anx_live_d8f58b73f847db12c222ffda84729f1234bdf7817ab4123f"
    hashed_token = hashlib.sha256(mock_token.encode("utf-8")).hexdigest()
    
    # cursor mock fetchone returns (id, name, is_active) for SELECT statement
    mock_conn, mock_cursor = get_mock_db(
        fetchone_val=(101, "CRM-System", True)
    )
    # Mock COUNT statement first then mock SELECT statement
    mock_cursor.fetchone.side_effect = [(10,), (101, "CRM-System", True)]
    
    with patch("app.helpers.auth.get_db_connection", return_value=mock_conn):
        result = await verify_api_key(api_key_header=mock_token)
        
        assert result == "CRM-System"
        
        # Verify lookup was executed using the hashed token
        lookup_args = mock_cursor.execute.call_args_list[1][0][1]
        assert lookup_args[0] == hashed_token, "Database query must look up hashed key"
        print("-> Test 3 (Hashed API Key Verification): PASSED")

async def test_legacy_apikey_auto_migration():
    print("\n4. Testing legacy plaintext API key auto-migration path...")
    
    legacy_plaintext_token = "anx_live_d8f58b73f847db12c222ffda84729f1234bdf7817ab4123f"
    hashed_token = hashlib.sha256(legacy_plaintext_token.encode("utf-8")).hexdigest()
    
    mock_conn, mock_cursor = get_mock_db()
    # Mock queries:
    # 1. COUNT of keys = 1
    # 2. SELECT with hashed token (returns None, key is legacy plaintext)
    # 3. SELECT with legacy plaintext token (returns (101, "CRM-System", True))
    mock_cursor.fetchone.side_effect = [
        (1,), 
        None, 
        (101, "CRM-System", True)
    ]
    
    with patch("app.helpers.auth.get_db_connection", return_value=mock_conn):
        result = await verify_api_key(api_key_header=legacy_plaintext_token)
        
        assert result == "CRM-System", "Should successfully verify legacy key"
        
        # Verify database update to hashed key was executed
        queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
        args = [call[0][1] if len(call[0]) > 1 else None for call in mock_cursor.execute.call_args_list]
        
        update_query = queries[-2]
        update_args = args[-2]
        
        assert "UPDATE api_keys SET api_key" in update_query, "Should execute migration query"
        assert update_args[0] == hashed_token, "Should update to hashed token"
        assert update_args[1] == 101, "Should update the legacy key record ID"
        print("-> Test 4 (Legacy API Key Auto-Migration): PASSED")

async def test_update_config_ignores_masked_keys():
    print("\n5. Testing config update ignoring masked key values...")
    
    # Mock current config settings
    settings.openai_api_key = "real-openai-api-key-1234"
    
    from app.schemas.config_schemas import ConfigUpdateRequest
    payload = ConfigUpdateRequest(
        openai_api_key="sk-op...3efd", # Masked key from frontend
        services={"web_crawler": True}
    )
    
    with patch("app.routes.config_routes._update_env_file") as mock_update_env:
        await update_active_configuration(payload)
        
        # Assert the real API key in settings was NOT updated
        assert settings.openai_api_key == "real-openai-api-key-1234", "Real key must not be overwritten"
        mock_update_env.assert_not_called(), "Should not call update_env_file for masked keys"
        print("-> Test 5 (Masked Keys Ignored on Update): PASSED")

async def test_atomic_env_file_update():
    print("\n6. Testing atomic write to .env file to prevent corruption...")
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_env_path = os.path.join(tmpdir, ".env")
        with open(test_env_path, "w", encoding="utf-8") as f:
            f.write("OPENAI_API_KEY=original_key\nOTHER_VAR=value\n")
            
        with patch("app.routes.config_routes.os.path.join", return_value=test_env_path):
             
            _update_env_file("OPENAI_API_KEY", "new_secure_key")
            
            # Read and verify updated env file
            with open(test_env_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            assert "OPENAI_API_KEY=new_secure_key" in content
            assert "OTHER_VAR=value" in content
            assert not os.path.exists(test_env_path + ".tmp"), "Temp file should be cleaned up"
            print("-> Test 6 (Atomic Env Update): PASSED")

async def main():
    print("=========================================")
    print("STARTING API KEY SECURITY VERIFICATION SUITE")
    print("=========================================")
    try:
        await test_apikey_creation_and_hashing()
        await test_apikey_listing_masked()
        await test_verify_hashed_apikey()
        await test_legacy_apikey_auto_migration()
        await test_update_config_ignores_masked_keys()
        await test_atomic_env_file_update()
        print("=========================================")
        print("ALL API KEY SECURITY TESTS PASSED SUCCESSFULLY!")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"[FAIL] TEST SUITE FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] UNEXPECTED ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
