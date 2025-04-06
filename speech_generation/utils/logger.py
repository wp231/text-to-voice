import os
import sys
import time
import logging
import logging.handlers

LOG_FILE = f'logs/{time.strftime("%Y%m%d_%H%M%S")}/app.log'

LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s [%(levelname)s] - %(message)s'


def create_log_folder() -> None:
    log_dir = os.path.normpath(LOG_FILE) 
    log_dir = os.path.dirname(log_dir)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

def setup_logger() -> logging.Logger:
    logging.getLogger().setLevel(logging.ERROR)

    logger = logging.getLogger("cli_app")
    logger.setLevel(LOG_LEVEL)

    if logger.hasHandlers():
        return logger
    
    create_log_folder()

    # 檔案輸出
    file_handler = logging.handlers.RotatingFileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)

    # 終端機輸出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()
