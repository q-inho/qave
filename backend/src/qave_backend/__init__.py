"""Compatibility exports for legacy qave_backend imports.

Primary APIs now live under the `qave` package namespace.
"""

from qave_backend.simulator.backend_a import simulate_backend_a

__all__ = ["simulate_backend_a"]
