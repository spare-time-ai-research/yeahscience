from sys import stdout

LOGGING_CONFIG: dict = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": stdout,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}
