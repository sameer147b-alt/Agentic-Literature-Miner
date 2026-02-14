"""
Professional Logging Module
Centralised logger for all agents in the Multi-Agent Literature Miner.

Writes structured logs to logs/system.log and to the console.
Tracks agentic handoffs, API response metrics, and general events.
"""

import logging
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "system.log")

# Ensure logs/ directory exists on first import
os.makedirs(LOG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Custom Formatter
# ---------------------------------------------------------------------------


class AgentFormatter(logging.Formatter):
    """
    Structured format:  TIMESTAMP | LEVEL | AGENT | MESSAGE

    Example:
        2026-02-13 18:20:05 | INFO  | Scraper | [API] PubMed | 200 | 1.23s | 50 results
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        level = record.levelname.ljust(5)
        agent = getattr(record, "agent", record.name).ljust(10)
        return f"{timestamp} | {level} | {agent} | {record.getMessage()}"


# ---------------------------------------------------------------------------
# Logger Factory
# ---------------------------------------------------------------------------

_formatter = AgentFormatter()

# Shared file handler (created once, reused by all loggers)
_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_formatter)

# Console handler
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_formatter)


def get_logger(agent_name: str) -> logging.Logger:
    """
    Return a logger tagged with the given agent name.

    Usage:
        from logger import get_logger
        log = get_logger("Scraper")
        log.info("[API] PubMed | 200 | 1.23s | 50 results")
        log.info("[HANDOFF] Scraper → Indexer | payload=data/abstracts.json")
    """
    logger = logging.getLogger(f"lit-miner.{agent_name}")

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_file_handler)
        logger.addHandler(_console_handler)

    # Attach agent name so the formatter can use it
    logger = logging.LoggerAdapter(logger, {"agent": agent_name})
    return logger


# ---------------------------------------------------------------------------
# Convenience: write an initial boot entry when the module is first imported
# ---------------------------------------------------------------------------

_boot_logger = get_logger("System")
_boot_logger.info("Logging system initialised — output → %s", LOG_FILE)
