import logging

from pfs.settings import LOG_LEVEL


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # stream formatter
    stream_formatter = logging.Formatter(
        fmt='%(asctime)s :: %(module)s.%(funcName)s:%(lineno)s [%(process)d] [%(levelname)s] :: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # stream handler
    stream_out_handler = logging.StreamHandler()
    stream_out_handler.setFormatter(stream_formatter)
    stream_out_handler.setLevel(LOG_LEVEL)
    logger.addHandler(stream_out_handler)

    return logger