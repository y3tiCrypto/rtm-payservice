import logging
import json
import sys
from app.config import settings

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logging():
    if settings.structured_logging:
        root_logger = logging.getLogger()
        
        # Clear existing handlers to avoid duplicate output
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        
        # Redirect standard uvicorn loggers to use the structured format via propagation
        for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
            logger = logging.getLogger(logger_name)
            logger.handlers = []
            logger.propagate = True
