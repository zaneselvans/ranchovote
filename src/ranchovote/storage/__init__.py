"""Durable persistence interfaces and backends for contest traces.

The `storage` package is distinct from `io` because persistence has different concerns
from serialization. Storage code decides how runs are written, indexed, queried, and
reconstructed over time, while `io` code is only concerned with format conversion.
"""
