import logging
import os


def setup_logging(default_level: str | int = "DEBUG") -> None:
    """Configure project-wide logging and silence noisy debug loggers."""
    level_name = os.getenv("LOG_LEVEL", str(default_level)).upper()
    level = getattr(logging, level_name, logging.DEBUG)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Keep global DEBUG, but quiet down noisy modules.
    logging.getLogger("matplotlib").setLevel(logging.CRITICAL)
    logging.getLogger("websockets").setLevel(logging.CRITICAL)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    logging.getLogger("kaleido").setLevel(logging.CRITICAL)
    logging.getLogger("choreographer").setLevel(logging.CRITICAL)
    logging.getLogger("browser_proc").setLevel(logging.CRITICAL)

