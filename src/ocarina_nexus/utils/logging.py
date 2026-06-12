from loguru import logger
from ocarina_nexus.config import LOG_FILE, LOG_LEVEL


def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.add(LOG_FILE, rotation="10 MB", level=LOG_LEVEL)
    return logger
