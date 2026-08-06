"""
/// <summary>
/// Generator of IDs for uploaded files (ArioNex File ID Generator)
/// </summary>
/// <remarks>
/// This module provides a thread-safe counter for generating unique IDs for uploaded files.
/// It is used as a temporary replacement for the database sequence during development.
///
/// Important: in production, use PostgreSQL SERIAL/SEQUENCE or UUID instead.
/// The current counter is kept in memory and resets after a server restart.
/// </remarks>
"""

import threading

# Global counter with a lock for thread-safety
_lock = threading.Lock()
_file_id_counter: int = 100
_initialized: bool = False


def get_next_file_id() -> int:
    """
    /// <summary>
    /// Generates a unique incremental ID for uploaded files
    /// </summary>
    """
    global _file_id_counter, _initialized
    with _lock:
        if not _initialized:
            from app.core.database import get_db_connection
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("SELECT COALESCE(MAX(id), 100) FROM documents;")
                    max_id = cur.fetchone()[0]
                    _file_id_counter = max(int(max_id), 100)
                conn.close()
                _initialized = True
            except Exception:
                # If the database cannot be reached at startup, continue with the default value
                pass
                
        _file_id_counter += 1
        return _file_id_counter
