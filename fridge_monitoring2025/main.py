import logging
import logging.config
import os
import pathlib
import time
from bluefors import BlueforsFridge
from constants import MonitoringError, InfluxDbError, MonitoringWarning
from file_observer import DirectoryObserver

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent


def init_logging() -> None:
    logfilename = DIRECTORY_OF_THIS_FILE / f"monitoring_{os.environ["USERNAME"]}.log"

    dict_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {"format": "%(levelname)-8s - %(message)s"},
            "timestamp": {
                "format": "%(asctime)s - %(levelname)-8s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "logfile": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "timestamp",
                "filename": logfilename,
                "maxBytes": 100_000_000,  # 100 MB
                "backupCount": 3,
            },
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "simple",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["stderr", "stdout", "logfile"],
        },
    }
    logging.config.dictConfig(dict_config)


logger = logging.getLogger(__file__)


def main():
    init_logging()
    if True:
        # Run monitoring
        fridge = BlueforsFridge.factory()
        observer = DirectoryObserver(fridge=fridge)
        while True:
            try:
                observer.poll()
            except InfluxDbError as e:
                logger.exception(e)
                fridge.reset_influx_db()
            except MonitoringError as e:
                logger.error(e)
            except MonitoringWarning as e:
                logger.warning(e)
            except Exception as e:
                logger.exception(e)
            time.sleep(10.0)

    if False:
        # Parse all files: Use to test the parser
        fridge = BlueforsFridge.factory()
        for f in fridge.log_folder.glob("**/*.log"):
            fridge.log_influx_file(f)


if __name__ == "__main__":
    main()
