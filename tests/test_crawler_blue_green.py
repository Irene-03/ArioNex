"""
/// <summary>
/// Automated test and verification file for the crawler blue-green switch transaction (Crawler Blue-Green Switch Verification Tests)
/// </summary>
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch

# Add the project path so the app package can be detected
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from app.services.workers.crawler.staging import _commit_staged_data

# Helper to create a mock database connection
def get_mock_db(temp_count=0, raise_switch_err=False):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # We mock execution. The second execute is SELECT COUNT(*)
    # The third execute is DELETE
    # The fourth execute is UPDATE
    def mock_execute(query, args=None):
        if "SELECT COUNT(*)" in query:
            # return count based on temp_count
            if hasattr(mock_cursor, "fetchone_results"):
                mock_cursor.fetchone.return_value = mock_cursor.fetchone_results.pop(0)
            else:
                mock_cursor.fetchone.return_value = (temp_count,)
        elif "DELETE FROM pg_supervisor" in query and "label = %s" in query and raise_switch_err:
            raise Exception("Database execution error during DELETE")
        return None

    mock_cursor.execute.side_effect = mock_execute
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor

def test_blue_green_success():
    print("1. Testing Blue-Green index switch under normal successful conditions...")
    
    mock_conn, mock_cursor = get_mock_db(temp_count=2)
    mock_cursor.fetchone_results = [(2,), (2,)] # For count checks

    mock_staged_files = ["crawl-staging/job_success/file1.json"]
    mock_file_content = json.dumps({"chunks": ["Chunk A", "Chunk B"]}).encode("utf-8")
    
    with patch("app.services.workers.crawler.staging.storage_manager.list_objects", return_value=mock_staged_files), \
         patch("app.services.workers.crawler.staging.storage_manager.get_object_data", return_value=mock_file_content), \
         patch("app.services.workers.crawler.staging._get_embedding_with_retry", return_value=[0.1]*3072), \
         patch("app.services.workers.crawler.staging.get_db_connection", return_value=mock_conn), \
         patch("app.services.workers.crawler.staging.storage_manager.delete_objects_in_prefix") as mock_delete_minio:
        
        total = _commit_staged_data(job_id="job_success", label="live_index")
        assert total == 2, f"Expected 2 total indexed chunks, got {total}"
        
        # Verify that DELETE and UPDATE were executed
        executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
        
        assert any("SELECT COUNT(*)" in q for q in executed_queries), "Should verify temporary count"
        assert any("DELETE FROM pg_supervisor WHERE label = %s" in q for q in executed_queries), "Should delete old live label"
        assert any("UPDATE pg_supervisor SET label = %s WHERE label = %s" in q for q in executed_queries), "Should swap labels"
        
        print("-> Test 1 (Normal Blue-Green Switch): PASSED")

def test_blue_green_empty_staging():
    print("\n2. Testing Blue-Green switch preservation when staging is empty...")
    
    # temp_count is 0 to simulate empty temporary staging in DB
    mock_conn, mock_cursor = get_mock_db(temp_count=0)
    mock_cursor.fetchone_results = [(0,), (0,)]

    mock_staged_files = ["crawl-staging/job_empty/file1.json"]
    mock_file_content = json.dumps({"chunks": []}).encode("utf-8") # Empty chunks
    
    with patch("app.services.workers.crawler.staging.storage_manager.list_objects", return_value=mock_staged_files), \
         patch("app.services.workers.crawler.staging.storage_manager.get_object_data", return_value=mock_file_content), \
         patch("app.services.workers.crawler.staging.get_db_connection", return_value=mock_conn), \
         patch("app.services.workers.crawler.staging.storage_manager.delete_objects_in_prefix"):
        
        try:
            _commit_staged_data(job_id="job_empty", label="live_index")
            assert False, "Should have raised ValueError due to empty staging"
        except ValueError as val_err:
            assert "No temporary crawled data found" in str(val_err)
            
            # Verify that DELETE (on live label) was NOT executed
            executed_calls = mock_cursor.execute.call_args_list
            delete_live_calls = [
                call for call in executed_calls
                if "DELETE FROM pg_supervisor" in call[0][0] and "label = %s" in call[0][0] and call[0][1] == ("live_index",)
            ]
            assert len(delete_live_calls) == 0, "Should NOT delete live label"
            
            update_live_calls = [
                call for call in executed_calls
                if "UPDATE pg_supervisor" in call[0][0] and call[0][1] == ("live_index", "crawled_temp:job_empty")
            ]
            assert len(update_live_calls) == 0, "Should NOT swap labels"
            
            print("-> Test 2 (Empty Staging Preservation): PASSED")

def test_blue_green_rollback():
    print("\n3. Testing Blue-Green switch rollback on database failure...")
    
    # Mock database to raise error during DELETE
    mock_conn, mock_cursor = get_mock_db(temp_count=3, raise_switch_err=True)
    mock_cursor.fetchone_results = [(3,), (3,)]

    mock_staged_files = ["crawl-staging/job_rollback/file1.json"]
    mock_file_content = json.dumps({"chunks": ["Chunk 1", "Chunk 2", "Chunk 3"]}).encode("utf-8")
    
    with patch("app.services.workers.crawler.staging.storage_manager.list_objects", return_value=mock_staged_files), \
         patch("app.services.workers.crawler.staging.storage_manager.get_object_data", return_value=mock_file_content), \
         patch("app.services.workers.crawler.staging._get_embedding_with_retry", return_value=[0.1]*3072), \
         patch("app.services.workers.crawler.staging.get_db_connection", return_value=mock_conn), \
         patch("app.services.workers.crawler.staging.storage_manager.delete_objects_in_prefix"):
        
        try:
            _commit_staged_data(job_id="job_rollback", label="live_index")
            assert False, "Should have raised database exception"
        except Exception as db_err:
            # We expect either the switch exception or the outer catch exception (which wraps clean up)
            assert "Database execution error during DELETE" in str(db_err) or "Database execution error during DELETE" in str(db_err.__cause__ or "")
            
            # Verify rollback was called on the connection
            assert mock_conn.rollback.called, "Should trigger transaction rollback on the database connection"
            
            # Verify cleanup deletion of temp chunks was initiated
            executed_calls = mock_cursor.execute.call_args_list
            cleanup_calls = [
                call for call in executed_calls
                if "DELETE FROM pg_supervisor" in call[0][0] and call[0][1] == ("crawled_temp:job_rollback",)
            ]
            assert len(cleanup_calls) > 0, "Should attempt cleanup of temp label"
            
            print("-> Test 3 (Transaction Rollback): PASSED")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING CRAWLER BLUE-GREEN SWITCH TESTS")
    print("=========================================")
    try:
        test_blue_green_success()
        test_blue_green_empty_staging()
        test_blue_green_rollback()
        print("=========================================")
        print("ALL CRAWLER BLUE-GREEN TESTS PASSED SUCCESSFULLY!")
        print("=========================================")
        sys.exit(0)
    except AssertionError as ae:
        print(f"[ERROR] TEST SUITE FAILED: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] UNEXPECTED ERROR: {str(e)}")
        sys.exit(1)
