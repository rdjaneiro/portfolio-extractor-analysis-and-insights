"""
Environment Variable Manager for dashCoachAI Application
=======================================================

This module handles loading and management of environment variables from different .env files
based on the current execution environment (development, production, test).

FUNCTIONALITY:
-------------
1. Determines the current environment from APP_ENV environment variable
2. Loads environment variables from appropriate .env files in a specific order
3. Provides utility functions to access environment information

LOADING ORDER:
------------
Environment variables are loaded in this specific order, with earlier files taking precedence:

1. .env.{environment} - Environment-specific configuration (development/production/test)
2. .env.local - Local overrides for development (not loaded in test environment)
3. .env - Default fallback values

USAGE:
-----
1. Set APP_ENV environment variable to select the environment:
   - export APP_ENV=development (default if not specified)
   - export APP_ENV=production
   - export APP_ENV=test

2. Import this module early in your application:
   - from env_manager import load_environment_variables, get_environment

3. Access environment variables using os.getenv():
   - import os
   - debug_mode = os.getenv("DEBUG", "False").lower() == "true"

ENVIRONMENT FILES:
----------------
- .env                - Default values shared across all environments
- .env.development    - Development-specific settings
- .env.production     - Production-specific settings
- .env.test           - Test-specific settings (used for automated tests)
- .env.local          - Personal overrides (not committed to version control)

NOTES:
-----
- Environment-specific settings (.env.{environment}) take precedence over .env
- Local settings (.env.local) override environment settings, but aren't loaded in test env
- All .env files should be excluded from version control (via .gitignore)
- Use .env.example as a template for required variables (safe to commit to version control)
"""

import os
from dotenv import load_dotenv
from pathlib import Path
import logging
from log_manager import get_logger
# Get the logger
logger = logging.getLogger("env_manager")

# Define environment types
ENV_DEVELOPMENT = 'development'
ENV_PRODUCTION = 'production'
ENV_TEST = 'test'
ENV_LOCAL = 'local'

def get_environment():
    """
    Get the current environment from the APP_ENV environment variable.
    Defaults to 'development' if not set.
    """
    return os.environ.get('APP_ENV', ENV_DEVELOPMENT).lower()

def load_environment_variables():
    """
    Load environment variables from the appropriate .env file.

    The loading order is:
    1. .env.{environment} - Environment-specific variables
    2. .env.local - Local overrides (if exists, not loaded in test environment)
    3. .env - Default variables

    Later loaded files won't override previously set variables.
    """
    env = get_environment()
    base_path = Path(__file__).parent

    # Start with environment-specific file
    env_file = base_path / f".env.{env}"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")

    # Load local overrides (except in test environment)
    if env != ENV_TEST:
        local_env_file = base_path / ".env.local"
        if local_env_file.exists():
            load_dotenv(local_env_file)
            logger.info(f"Loaded local overrides from {local_env_file}")

    # Finally load the default .env file
    default_env_file = base_path / ".env"
    if default_env_file.exists():
        load_dotenv(default_env_file)
        logger.info(f"Loaded default environment variables from {default_env_file}")

    # Print the current environment
    logger.info(f"Running in {env} environment")

# Load environment variables when this module is imported
load_environment_variables()