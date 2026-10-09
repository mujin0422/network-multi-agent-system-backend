import logging

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
DATE_FORMAT = "%H:%M:%S"

def setupLogging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

def getLogger(name: str | None = None) -> logging.Logger:
    setupLogging()
    return logging.getLogger(name)
