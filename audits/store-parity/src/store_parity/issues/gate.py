"""Compatibility entry point for acceptance-gate evaluation."""

from store_parity.issues.classification import GatePolicy, evaluate_acceptance_gate
from store_parity.issues.models import GateResult

__all__ = ["GatePolicy", "GateResult", "evaluate_acceptance_gate"]
