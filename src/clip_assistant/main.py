"""
Clase Principal para la V2
@author: crizconzeta
@date: 2025-06-15
"""

import logging
import sys
from pathlib import Path

from .assistant import ClipAssistant
from .config import Settings

# Oi, there's a log.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    stream=sys.stdout,
)


def run():
    """Loads config, creates the assistant, and runs it until the end of time"""
    project_root = Path(__file__).resolve().parent.parent.parent
    config_path = project_root / "config.yaml"

    logging.info("Attempting to load configuration from: %s", config_path)

    settings = Settings.load_from_yaml(str(config_path))

    if not settings:
        sys.exit(1)  # A swift and merciful end.

    assistant = ClipAssistant(settings)
    assistant.run()


if __name__ == "__main__":
    run()
