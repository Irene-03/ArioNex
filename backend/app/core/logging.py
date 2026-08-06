"""
/// <summary>
/// ArioNex centralized logging configuration (ArioNex Logging Configuration)
/// </summary>
/// <remarks>
/// All system logs produced by this application are generated in English with an organized structure
/// at various levels and sent to the console.
/// </remarks>
"""

import logging
import sys

def setup_logging() -> None:
    """
    /// <summary>
    /// Set up and configure the Python logging module
    /// </summary>
    /// <remarks>
    /// The log output format includes timestamp, file name, log level, and the log message in English.
    /// </remarks>
    """
    # Reconfigure stdout and stderr to handle UTF-8 Persian/Arabic text correctly on Windows/etc.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set the log level for third-party libraries to reduce console noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("psycopg2").setLevel(logging.WARNING)
    
    logger = logging.getLogger("arionex")
    logger.info("ArioNex Enterprise Logging System Initialized Successfully.")
