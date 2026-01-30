# Built In Dependencies
import os
import sys
import logging

# Internal Dependencies
from led_mon.led_system_monitor import main

if __name__ == "__main__":
    level = logging.WARNING
    if os.getenv("LOG_LEVEL", "").lower() == "debug":
        level = logging.DEBUG
    elif os.getenv("LOG_LEVEL", "").lower() == "error":
        level = logging.ERROR
    elif os.getenv("LOG_LEVEL", "").lower() == "info":
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main(sys.argv)