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

    path = Path(__file__).parent.parent.joinpath('logging.yaml')
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


def message_general(message: str, text: str, ancestors: str, line: int = None) -> str:
    if message[-1] == '.':
        message = message[:-1]
    text = f"Warning: {message}, while processing '{text}'"
    if ancestors:
        text += f' in parse tree elements [{ancestors}]'
    if line is not None:
        text += f' at line {line}'
    return text


def message_syntax(owner: str, text: str, message: str, category: str) -> str:
    return f"{message}. Handling '{text}' for {category} '{owner}'. Ignoring the definition"


def message_bad_value(owner: str, key: str, message: str, category: str) -> str:
    return f"For attribute '{key}' of {category} '{owner}': {message}. Ignoring the definition"


def message_unknown_attribute(owner: str, key: str, category: str = None) -> str:
    if category:
        return f"Unknown attribute '{key}' defined for {category} '{owner}'. Ignoring the definition"
    else:
        return f"Unknown attribute '{key}' defined for '{owner}'. Ignoring the definition"
