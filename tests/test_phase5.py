"""
/// <summary>
/// ArioNex Phase 5 automated test and verification file (ArioNex Phase 5 Verification Script)
/// </summary>
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project path so the app package can be detected
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.integrations.telegram_bot import (
    start_telegram_bot_service,
    stop_telegram_bot_service,
    start_command,
    help_command,
    message_handler,
    get_chat_history,
    update_chat_history
)

client = TestClient(app)

def test_fastapi_endpoints():
    # Setup mock cursor to return 0 for count of API keys
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    print("Testing REST API Endpoints...")
    from app.helpers.auth import verify_api_key
    app.dependency_overrides[verify_api_key] = lambda: "test_user"
    
    from unittest.mock import patch
    with patch("app.helpers.auth.get_db_connection") as mock_get_db, \
         patch("app.services.retrieval.query_router.synthesize_rag_response") as mock_synthesize, \
         patch("app.services.retrieval.analyst.analyst_agent.execute_analysis") as mock_execute:
         
        mock_get_db.return_value = mock_conn
        mock_execute.return_value = "مجموع بدهکاری اسناد از نوع سند چک برابر با ۶۲۳,۳۴۶ ریال می‌باشد."
        mock_synthesize.return_value = {
            "answer": "قوانین استخدام شرکت شامل ساعات کاری ۸:۰۰ الی ۱۶:۳۰ می‌باشد.",
            "sources": [{"name": "document.txt"}],
            "is_safe": True
        }
        
        try:
            # 1. Test the system health endpoint
            response = client.get("/health")
            print(f"GET /health: {response.status_code}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "online"
            assert "telegram_bot" in data["active_features"]
            
            # 2. Test retrieving the feature toggles
            response = client.get("/v1/config")
            print(f"GET /v1/config: {response.status_code}")
            assert response.status_code == 200
            config_data = response.json()
            assert "services" in config_data
            assert "integrations" in config_data
            
            # 3. Test dynamic settings changes
            update_payload = {
                "services": {"entity_extractor": True},
                "integrations": {"telegram_bot": False}
            }
            response = client.post("/v1/config", json=update_payload)
            print(f"POST /v1/config: {response.status_code}")
            assert response.status_code == 200
            res_json = response.json()
            assert res_json["status"] == "success"
            
            # Restore settings to their initial state
            restore_payload = {
                "services": {"entity_extractor": False},
                "integrations": {"telegram_bot": True}
            }
            client.post("/v1/config", json=restore_payload)
            
            # 4. Test retrieving the website chat widget script
            response = client.get("/v1/widget.js")
            print(f"GET /v1/widget.js: {response.status_code}")
            assert response.status_code == 200
            assert "arionex-widget-bubble" in response.text
            assert "application/javascript" in response.headers["content-type"]
            
            # 5. Test the chat widget message endpoint
            chat_payload = {
                "query": "مجموع بدهکاری اسناد نوع چک چقدر است؟",
                "session_id": "test_widget_session"
            }
            response = client.post("/v1/widget/chat", json=chat_payload)
            print(f"POST /v1/widget/chat: {response.status_code}")
            assert response.status_code == 200
            chat_response = response.json()
            assert "answer" in chat_response
            assert "sources" in chat_response
            
            # 6. Test the general RAG query endpoint
            query_payload = {
                "query": "قوانین استخدام شرکت چیست؟",
                "session_id": "test_rest_session"
            }
            response = client.post("/v1/query", json=query_payload)
            print(f"POST /v1/query: {response.status_code}")
            assert response.status_code == 200
            query_response = response.json()
            assert "answer" in query_response
            
            print(" REST API Endpoints checks PASSED.\n")
        finally:
            app.dependency_overrides.clear()

def test_telegram_bot_session_manager():
    print("Testing Telegram Bot Session Manager...")
    
    chat_id = 987654321
    # Clear any possible test history
    history = get_chat_history(chat_id)
    history.clear()
    
    # Test adding a message to the user session
    update_chat_history(chat_id, "سلام", "درود بر شما")
    history = get_chat_history(chat_id)
    
    assert len(history) == 2
    assert history[0]["Human"] == "سلام"
    assert history[1]["AI"] == "درود بر شما"
    
    # Test the history cap limit to the latest 10 messages
    for i in range(15):
        update_chat_history(chat_id, f"سوال {i}", f"پاسخ {i}")
        
    history = get_chat_history(chat_id)
    assert len(history) <= 10
    print(" Telegram Bot Session Manager checks PASSED.\n")

async def test_telegram_bot_handlers():
    print("Testing Telegram Bot Async Handlers...")
    
    # Mock the Telegram update and context
    mock_update = MagicMock()
    mock_update.effective_chat.id = 123456789
    mock_update.message = MagicMock()
    mock_update.message.text = "مجموع بدهکاری چیست؟"
    mock_update.message.reply_text = AsyncMock()
    
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    
    from unittest.mock import patch
    with patch("app.services.retrieval.query_router.synthesize_rag_response") as mock_synthesize, \
         patch("app.services.retrieval.analyst.analyst_agent.execute_analysis") as mock_execute:
         
        mock_execute.return_value = "مجموع بدهکاری اسناد از نوع سند چک برابر با ۶۲۳,۳۴۶ ریال می‌باشد."
        mock_synthesize.return_value = {
            "answer": "قوانین استخدام شرکت شامل ساعات کاری ۸:۰۰ الی ۱۶:۳۰ می‌باشد.",
            "sources": [{"name": "document.txt"}],
            "is_safe": True
        }
        
        # 1. Test the start handler
        await start_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called()
        welcome_call_args = mock_update.message.reply_text.call_args[0][0]
        assert "آریونکس" in welcome_call_args
        print("  Start Handler check PASSED.")
        
        # 2. Test the help handler
        await help_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called()
        help_call_args = mock_update.message.reply_text.call_args[0][0]
        assert "راهنمای استفاده" in help_call_args
        print("  Help Handler check PASSED.")
        
        # 3. Test the text message handler and connection to the RAG engine
        mock_update.message.reply_text = AsyncMock()
        await message_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_called()
        reply_args = mock_update.message.reply_text.call_args[0][0]
        assert len(reply_args) > 0
        print("  Message Handler RAG Connection check PASSED.")
        
    print(" Telegram Bot Async Handlers checks PASSED.\n")

async def test_telegram_lifecycle_and_safety():
    print("Testing Telegram Bot Lifecycle & Safety Airlock...")
    
    # Mock the python-telegram-bot packages to prevent sending real connections
    with patch("app.services.integrations.telegram_bot.ApplicationBuilder") as mock_builder:
        mock_app = MagicMock()
        mock_app.initialize = AsyncMock()
        mock_app.start = AsyncMock()
        mock_app.updater = MagicMock()
        mock_app.updater.start_polling = AsyncMock()
        
        mock_builder.return_value.token.return_value.build.return_value = mock_app
        
        # Test the feature being enabled and the bot starting up successfully
        settings.telegram_bot_token = "mock_token_123"
        settings.integrations.telegram_bot = True
        
        await start_telegram_bot_service()
        
        mock_app.initialize.assert_called_once()
        mock_app.start.assert_called_once()
        mock_app.updater.start_polling.assert_called_once()
        print("  Bot Startup sequence completed without blocking.")
        
        # Test the bot shutting down successfully
        mock_app.stop = AsyncMock()
        mock_app.shutdown = AsyncMock()
        mock_app.updater.stop = AsyncMock()
        
        await stop_telegram_bot_service()
        
        mock_app.updater.stop.assert_called_once()
        mock_app.stop.assert_called_once()
        mock_app.shutdown.assert_called_once()
        print("  Bot Shutdown sequence completed successfully.")
        
    print(" Telegram Bot Lifecycle checks PASSED.\n")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING PHASE 5 AUTOMATED TEST SUITE")
    print("=========================================")
    try:
        test_fastapi_endpoints()
        test_telegram_bot_session_manager()
        
        # Run the async handlers in the current event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_telegram_bot_handlers())
        loop.run_until_complete(test_telegram_lifecycle_and_safety())
        
        print("=========================================")
        print("ALL PHASE 5 TESTS COMPLETED SUCCESSFULLY! ")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ TEST SUITE FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR IN TEST RUN: {str(e)}")
        sys.exit(1)
