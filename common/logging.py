import logging
import logging.config
import os
from pathlib import Path

import yaml

_logging_initialized = False


# noinspection PyUnresolvedReferences
def _initialize_logging():
    logging.FINE = 8
    logging.addLevelName(logging.FINE, "FINE")

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


class BraceString(str):
    def __mod__(self, other):
        try:
            return self.format(*other)
        except Exception:
            pass

    def __str__(self):
        return self


# noinspection PyUnresolvedReferences
class EnhancedLoggingAdapter(logging.LoggerAdapter):

    def __init__(self, logger, extra=None):
        super(EnhancedLoggingAdapter, self).__init__(logger, extra)

    def process(self, msg, kwargs):
        return BraceString(msg), kwargs

    def fine(self, message, *args, **kws):
        if self.isEnabledFor(logging.FINE):
            self._log(logging.FINE, message, args, **kws)


def configured_logger(name: str):
    global _logging_initialized
    if not _logging_initialized:
        _initialize_logging()
        _logging_initialized = True
    return EnhancedLoggingAdapter(logging.getLogger(name))


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
