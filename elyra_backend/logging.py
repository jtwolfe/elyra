import logging


def get_logger(name: str = "elyra_backend") -> logging.Logger:
    """
    Return a module-level logger configured with a sensible default.

    In Phase 1 this is intentionally simple: logs go to stdout with an
    INFO-level default. Deployments can override handlers/levels via the
    standard logging configuration mechanisms.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger



