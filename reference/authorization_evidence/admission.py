"""Offline verifier → authoritative single-deployment reservation. No actions invoked."""
from .core import require, Rejected
from .verifier import Verifier, Result

def admit(store, trust, request, invocation_index, ledger, checkpoint, before_reserve=None):
    result = Verifier(store, trust).authorize(request)
    if result.category != 'AUTHORIZED_WITH_BUDGET_PENDING':
        return result
    try:
        require(type(invocation_index) is int and 0 <= invocation_index < len(result.reservations),
                'INVALID', 'invocation index')
        grant = result.reservations[invocation_index]
        require(grant['deployment_id'] == ledger.deployment and ledger.public in grant['ledger_authorities'],
                'UNAUTHORIZED', 'ledger not principal-consented authority')
        require(checkpoint is not None, 'UNAVAILABLE', 'caller-held independent ledger checkpoint required')
        # Checkpoint is lower bound, never silently chosen from an untrusted bundle.
        # Verify the caller-held prefix and update budgets/nonces in one write transaction.
        outcome = ledger.reserve(checkpoint=checkpoint, before_write=before_reserve,
                                 **{k: v for k, v in grant.items() if k not in ('deployment_id','ledger_authorities')})
        return Result('RESERVED_NO_ACTION' if outcome == 'new_reservation' else 'ALREADY_RECORDED_NO_ACTION',
                      outcome, result.layers + ['atomic-budget-reservation'], [grant],
                      result.assumptions + ['local authoritative SQLite state/key and independent rollback checkpoint'])
    except Rejected as exc:
        return Result(exc.category, exc.detail, result.layers)
