"""Read-only export verification CLI. No network or tool execution."""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from .core import SCHEMA_DIGEST, Store, strict_json, Rejected, digest, canonical, require
from .verifier import Trust, Verifier

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export',required=True)
    parser.add_argument('--schema',required=True,help='revision-2 fenced schema Markdown')
    parser.add_argument('--schema-digest',required=True,help='independently pinned digest of canonical schema JSON')
    parser.add_argument('--principal',required=True,help='independently configured ed25519:public-key')
    parser.add_argument('--now',required=True)
    parser.add_argument('--history-as-of',required=True,help='independently trusted history freshness checkpoint')
    parser.add_argument('--authorization-request',help='local pre-call request JSON; no execution proof required')
    parser.add_argument('--active-intent',action='append',default=[],help='independently trusted current active Intent id, not export-provided')
    parser.add_argument('--max-export-bytes',type=int,default=64*1024*1024)
    args=parser.parse_args()
    try:
        require(args.max_export_bytes>0,'INVALID','byte limit')
        schema=strict_json(Path(args.schema).read_text().split('```json\n')[1].split('```')[0].encode())
        require(digest(canonical(schema))==args.schema_digest==SCHEMA_DIGEST,'UNSUPPORTED','schema pin')
        store,bundle=Store.directory(args.export,schema,args.max_export_bytes)
        verifier=Verifier(store,Trust(args.principal,args.schema_digest,args.now,args.history_as_of,frozenset(args.active_intent)))
        result=verifier.authorize(strict_json(Path(args.authorization_request).read_bytes())) if args.authorization_request else verifier.verify(bundle)
        print(json.dumps(asdict(result),ensure_ascii=False,indent=2))
        return 0 if result.category in ('VERIFIED_WITH_BUDGET_PENDING','AUTHORIZED_WITH_BUDGET_PENDING') else 2
    except (Rejected,OSError,ValueError,IndexError,RecursionError) as exc:
        print(json.dumps({'category':getattr(exc,'category','INVALID'),'detail':str(exc)}))
        return 2

if __name__=='__main__':sys.exit(main())
