"""Utility functions for CLI operations."""

import logging


def setup_logging(level: str) -> None:
    """Configure logging based on user-specified level.

    Args:
        level: Logging level (debug, info, warning, error, critical)
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
