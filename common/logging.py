import logging
import logging.config
import os
from pathlib import Path

import yaml

_logging_initialized = False
FINE = 8


def _initialize_logging():
    logging.FINE = FINE
    logging.addLevelName(FINE, "FINE")

    def fine(self, message, *args, **kws):
        if self.isEnabledFor(FINE):
            self._log(FINE, message, args, **kws)

    logging.Logger.fine = fine

    path = Path(__file__).parent.parent.joinpath('resources', 'logging.yaml')
    if os.path.exists(path):
        with open(path, 'rt') as f:
            try:
                config = yaml.safe_load(f.read())

                # Ensure the log file directory exists
                log_file = Path(config['handlers']['file']['filename'])
                os.makedirs(log_file.parent, exist_ok=True)

                logging.config.dictConfig(config)
                return
            except Exception as e:
                print(e)
                print('Error in Logging Configuration. Using default configs')
    else:
        print('Failed to load configuration file. Using default configs')


def configured_logger(name: str):
    global _logging_initialized
    if not _logging_initialized:
        _initialize_logging()
        _logging_initialized = True
    return logging.getLogger(name)
