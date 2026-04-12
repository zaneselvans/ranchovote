"""FastAPI-facing entry points for browser and API-based trace exploration.

The web package exposes application factories rather than a globally configured app so
tests and future deployment targets can choose their own storage dependencies.
"""
