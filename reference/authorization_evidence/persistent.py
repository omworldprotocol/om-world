"""Local persistent admission and recovery, with no action execution. Apache-2.0."""
import os
from .core import Rejected, require, canonical, strict_json
from .verifier import Result
from .admission import admit

def persistent_admit(store, binder, request, index, ledger, anchors, receipts):
    """All users of this deployment must use this store/lock order: anchor → ledger.

    Source keys/policy and anchor directory are caller-configured trust, not export data.
    Never turns a synthetic source receipt into a claim of a real status/time source.
    """
    try:
        require(binder is not None, 'UNAVAILABLE', 'real source configuration missing')
        receipts=strict_json(canonical(receipts))
        with anchors.locked():
            anchors._ledger_binding(ledger)
            value=anchors._load()
            ledger.audit(value['checkpoint'])
            # Persist authenticated source revisions even if status subsequently denies this
            # request: an observed cancellation must not be forgotten by replaying an old active list.
            records,now=binder.authenticate(receipts,value['sources'])
            updated={**value,'generation':value['generation']+1,'sources':records}
            anchors._write(updated)
            value=updated
            trust,records,now=binder.bind(store,request,receipts,value['sources'])
            intent_id=request['intent_ref']['id']
            require(intent_id in trust.active_intent_ids,'UNAUTHORIZED','authenticated status does not attest active Intent')
            def guard():
                _,_,wall=binder.bind(store,request,receipts,value['sources'])
                binder.current_bounds(store,request,index,wall)
            result=admit(store,trust,request,index,ledger,value['checkpoint'],before_reserve=guard)
            if result.category not in ('RESERVED_NO_ACTION','ALREADY_RECORDED_NO_ACTION'):
                return result
            try:
                anchored=anchors._advance(ledger,value)
            except (OSError,Rejected) as exc:
                return Result('WAITING_ANCHOR_NO_ACTION','ledger reservation may be committed; recover before any handoff: '+str(exc),
                              result.layers,result.reservations,result.assumptions+['no automatic release/re-execution'])
            test=any(v['evidence_kind']=='synthetic_test' for v in receipts.values())
            if test:
                result.category='TEST_'+result.category
            result.layers.append('durable-independent-local-checkpoint-and-source-binding')
            result.assumptions.extend(['source receipts are attributed claims, not proof of true real-world status/time',
                                      'local wall clock and independently protected store must actually be provisioned',
                                      'synthetic engineering input' if test else 'configured source-attestation policy; no truth certification'])
            return result
    except Rejected as exc:
        return Result(exc.category,exc.detail)
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        return Result('INVALID','malformed persistent admission input: '+str(exc))
    except OSError as exc:
        return Result('UNAVAILABLE','local anchor I/O failed; no execution handoff: '+str(exc))

