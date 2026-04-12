"""Format conversion helpers for human-readable or API-friendly representations.

The `io` package is separate from `storage` on purpose. Code here focuses on turning
domain objects into portable text-oriented shapes such as JSON-friendly dictionaries,
while the storage layer is responsible for durable persistence, schemas, and queries.
"""
