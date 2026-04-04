"""
logging_config.py
-----------------
Configures application-wide logging to both console and a rotating log file.
"""

import logging
import logging.handlers
import os


LOG_FILE = "bot.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_file: str = LOG_FILE, level: int = logging.INFO) -> None:
    """
    Set up root logger with:
      - A RotatingFileHandler (INFO+) writing to `log_file`
      - A StreamHandler (WARNING+) for console output
    Call once at application startup.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # capture everything; handlers filter

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- File handler (rotating, max 5 MB × 3 backups) ---
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # --- Console handler (warnings and above to keep CLI clean) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    logging.getLogger(__name__).info("Logging initialised — file: %s", os.path.abspath(log_file))
