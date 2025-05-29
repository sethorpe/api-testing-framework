# src/api_testing_framework/logger.py
import logging

# Configure the root logger for the project
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Expose a pre-configured logger for convenience
logger = logging.getLogger("api_testing_framework")
