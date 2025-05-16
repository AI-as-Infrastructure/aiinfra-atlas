"""ATLAS Targets Package

This package contains target configuration modules for the ATLAS application,
defining model configurations, database connections, and search parameters.
"""

# This file makes the targets directory a proper Python package
# allowing for dynamic import of target configurations

# Import all attributes from the blert_500 module
from .blert_500 import *