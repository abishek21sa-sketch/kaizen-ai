"""Observable-data statistical investigator for KAIZEN AI.

V0.4 deliberately stops at observational evidence. It ranks suspects and
records tests; it does not claim causal confirmation.
"""

from .engine import build_investigation_overview

__all__ = ["build_investigation_overview"]
