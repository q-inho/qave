"""Contract version source of truth for the public qave API."""

CURRENT_CONTRACT_VERSION = "0.1.0"
CONTRACT_VERSION = CURRENT_CONTRACT_VERSION


def contract_version() -> str:
    """Return the contract version stamped by this package build."""
    return CONTRACT_VERSION
