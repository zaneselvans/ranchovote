"""Shared application services used by interactive and programmatic interfaces.

The service layer sits above storage and below the UI or API entry points. It gives the
web app, TUI, and any future interface a common read model so they do not each invent
their own storage access patterns.
"""
