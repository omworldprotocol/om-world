"""Signed offline status/history/clock source binding. Apache-2.0.

Authentication proves attribution to configured source keys, not that a real source
has been provisioned or that a signed claim about the world is true.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from .core import (PROFILE, SCHEMA_DIGEST, require, canonical, digest, instant,
                   signing_digest, identity_bytes, Rejected)
from .verifier import Trust
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

@dataclass(frozen=True)
class Source:
    source_id: str
    authority: str
    max_age_seconds: int
    evidence_kind: str = 'source_attestation'

@dataclass(frozen=True)
class SourcePolicy:
    principal: str
    schema_digest: str
    status: Source
    history: Source
    clock: Source
    allow_synthetic: bool = False

COMMON = {'format','role','source_id','authority','revision','principal','schema_digest',
          'evidence_kind','as_of','issued_at','expires_at','payload','signature'}
PAYLOADS = {'status':{'active_intent_ids'}, 'history':{'identity_profile_digest','key_event_digests'},
            'clock':{'time_basis'}}

def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

class SourceBinder:
    def __init__(self, policy, wall_clock=utc_now):
        self.policy, self.wall_clock = policy, wall_clock
        require(policy.schema_digest == SCHEMA_DIGEST, 'UNSUPPORTED', 'source schema pin')
        identity_bytes(policy.principal)
        for source in [policy.status, policy.history, policy.clock]:
            identity_bytes(source.authority)
            require(isinstance(source.source_id,str) and source.source_id
                    and type(source.max_age_seconds) is int and source.max_age_seconds >= 0,
                    'INVALID', 'source identity/freshness policy')
            require(source.evidence_kind in ('source_attestation','synthetic_test'), 'INVALID', 'source class policy')

    def _validate(self, role, value, check_freshness=True, now=None):
        source = getattr(self.policy, role)
        require(isinstance(value,dict) and set(value)==COMMON, 'INVALID', 'closed source receipt shape')
        require(value['format']=='omworld.offline-source.v1' and value['role']==role
                and value['source_id']==source.source_id and value['authority']==source.authority,
                'UNAUTHORIZED', 'unconfigured source/role')
        require(value['principal']==self.policy.principal and value['schema_digest']==self.policy.schema_digest,
                'UNAUTHORIZED', 'source principal/schema binding')
        require(value['evidence_kind']==source.evidence_kind, 'UNAUTHORIZED', 'source class mismatch')
        require(value['evidence_kind']!='synthetic_test' or self.policy.allow_synthetic,
                'UNAVAILABLE', 'synthetic input refused outside explicit test policy')
        require(type(value['revision']) is int and 0 <= value['revision'] <= 9007199254740991,
                'INVALID', 'source revision')
        require(isinstance(value['payload'],dict) and set(value['payload'])==PAYLOADS[role],
                'INVALID', 'source payload shape')
        if role=='status':
            items=value['payload']['active_intent_ids']
            require(isinstance(items,list) and all(isinstance(x,str) and len(x)==71 and x.startswith('sha256:') and all(c in '0123456789abcdef' for c in x[7:]) for x in items) and len(set(items))==len(items),'INVALID','status digest list')
        elif role=='history':
            items=[value['payload']['identity_profile_digest']]
            events=value['payload']['key_event_digests']
            require(isinstance(events,list),'INVALID','history digest list')
            items+=events
            require(all(isinstance(x,str) and len(x)==71 and x.startswith('sha256:') and all(c in '0123456789abcdef' for c in x[7:]) for x in items) and len(set(events))==len(events),'INVALID','history digests')
        else:
            require(value['payload']['time_basis']=='UTC-source-attestation','UNSUPPORTED','clock evidence basis')
        require(instant(value['as_of']) <= instant(value['issued_at']) < instant(value['expires_at']),
                'INVALID', 'source time order')
        try:
            sig=bytes.fromhex(value['signature'])
            require(len(sig)==64 and sig.hex()==value['signature'],'INVALID','source signature encoding')
            Ed25519PublicKey.from_public_bytes(identity_bytes(source.authority)).verify(sig,signing_digest(value))
        except (ValueError,TypeError,InvalidSignature):
            require(False,'INVALID','source signature')
        if check_freshness:
            now = now or self.wall_clock()
            age=(instant(now)-instant(value['as_of'])).total_seconds()
            require(0 <= age <= source.max_age_seconds and instant(value['issued_at']) <= instant(now)
                    < instant(value['expires_at']), 'UNAVAILABLE', 'source stale/expired/future')
        return digest(canonical(value))

    def authenticate(self, receipts, prior):
        """Authenticate/pin high waters before request-specific authorization decisions."""
        require(isinstance(receipts,dict) and set(receipts)=={'status','history','clock'},
                'UNAVAILABLE','all configured source receipts required')
        require(isinstance(prior,dict),'INVALID','source high-water map')
        require(set(prior)<=set(receipts),'INVALID','unknown prior source role')
        now=self.wall_clock();records={}
        for role,value in receipts.items():
            h=self._validate(role,value,now=now)
            if role in prior:
                old=prior[role]
                require(isinstance(old,dict) and set(old)=={'receipt','digest','validated_at'},'INVALID','saved source record')
                require(self._validate(role,old['receipt'],check_freshness=False)==old['digest'],
                        'INVALID','saved source digest/attribution')
                previous=old['receipt']
                require(value['revision']>=previous['revision'],'UNAVAILABLE','source revision rollback')
                if value['revision']==previous['revision']:
                    require(h==old['digest'],'INVALID','same-revision source conflict')
                require(instant(value['as_of'])>=instant(previous['as_of']),'UNAVAILABLE','source as-of rollback')
            records[role]={'receipt':value,'digest':h,'validated_at':now}
        return records,now

    def bind(self, store, request, receipts, prior):
        """Bind exact export dependencies without retimestamping source snapshots."""
        records,now=self.authenticate(receipts,prior)
        times={v['as_of'] for v in receipts.values()}
        require(len(times)==1,'UNAVAILABLE','status/history/clock operation context not aligned')
        operation_time=receipts['clock']['as_of']
        require(receipts['clock']['payload']['time_basis']=='UTC-source-attestation',
                'UNSUPPORTED','clock evidence basis')
        manifest=store.resolve(request['dependency_manifest_ref'],'DependencyManifest')
        history=receipts['history']['payload']
        require(history['identity_profile_digest']==manifest['identity_profile_ref']['digest'],
                'UNAUTHORIZED','history bound to different identity profile')
        identity=store.artifact(manifest['identity_profile_ref'],'IdentityProfile')
        event_hashes=history['key_event_digests']
        require(isinstance(event_hashes,list) and all(isinstance(x,str) for x in event_hashes)
                and len(set(event_hashes))==len(event_hashes)
                and set(event_hashes)=={r['digest'] for r in identity['key_event_refs']},
                'UNAUTHORIZED','history completeness commitment differs from export')
        active=receipts['status']['payload']['active_intent_ids']
        require(isinstance(active,list) and all(isinstance(x,str) and len(x)==71 and x.startswith('sha256:') for x in active)
                and len(set(active))==len(active),'INVALID','active Intent list')
        intent=store.resolve(request['intent_ref'],'Intent')
        # Keep the source's actual as_of. Do not retimestamp an older history to local now.
        trust=Trust(self.policy.principal,self.policy.schema_digest,operation_time,operation_time,frozenset(active))
        return trust,records,now

    def current_bounds(self, store, request, index, wall_time):
        """Recheck finite authorization intervals against actual local wall time before reservation.

        Source snapshots can be bounded-stale within the configured max_age; this does not
        claim knowledge of later real cancellations. No action is executed by reservation.
        """
        from .core import check_time
        from .policy import allowed, within
        intent=store.resolve(request['intent_ref'],'Intent')
        acceptance=store.resolve(request['acceptance_ref'],'Acceptance')
        require(len(request['consent_refs'])==1,'UNAUTHORIZED','exact Consent')
        consent=store.resolve(request['consent_refs'][0],'Consent')
        require(type(index) is int and 0<=index<len(request['invocation_refs']),'INVALID','invocation index')
        invref=request['invocation_refs'][index];inv=store.resolve(invref,'Invocation');tool=store.resolve(inv['tool_entry_ref'],'ToolEntry')
        plan=store.resolve(acceptance['plan_ref'],'Plan')
        action=plan['ordered_actions'][inv['plan_index']]['action']
        require(instant(action['valid_from'])<=instant(wall_time)<instant(action['expires_at']),'UNAUTHORIZED','plan template expired before reservation')
        require(instant(tool['valid_from'])<=instant(wall_time),'UNAUTHORIZED','tool not active at reservation')
        for value in [intent,acceptance,consent]:
            check_time(value['issued_at'],value['expires_at'],wall_time)
        require(instant(wall_time)<=instant(acceptance['deadline']),'UNAUTHORIZED','deadline elapsed at reservation')
        for limits in [intent['constraints'],acceptance['action_limits'],consent['action_limits']]:
            require(allowed(limits,tool,inv,wall_time),'UNAUTHORIZED','scope expired before reservation')
        for ref in acceptance['delegation_refs']:
            credential=store.artifact(ref,'Delegation');check_time(credential['issued_at'],credential['expires_at'],wall_time)
            require(allowed(credential['action_limits'],tool,inv,wall_time),'UNAUTHORIZED','credential expired before reservation')
        policy=store.resolve(inv['deployment_policy_ref'],'DeploymentPolicy')
        restriction=store.artifact(policy['extra_requirements_ref'],'RestrictionProfile')
        check_time(restriction['not_before'],restriction['expires_at'],wall_time)
        require(not any(within(x,tool,inv,wall_time) for x in policy['deny_rules']),
                'UNAUTHORIZED','deployment deny at reservation')
        for ref in request['approval_refs']:
            value=store.resolve(ref,'InvocationApproval')
            if value['invocation_ref']==invref:check_time(value['issued_at'],value['expires_at'],wall_time)
