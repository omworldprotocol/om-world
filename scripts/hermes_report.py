#!/usr/bin/env python3
"""UPP L2 日报 — om-world. 只读自己->输出标准 JSON(host-runner 负责传输到 omw_server.db)。
用法: python3 hermes_report.py [--dry]  (--dry 美化; 默认单行 JSON)"""
import os,sys,json,sqlite3,datetime,glob,time,urllib.request
PROJECT_ID="om-world"
TODAY=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
def _sql(db,q,d=0):
    try:
        c=sqlite3.connect(f"file:{db}?mode=ro",uri=True,timeout=5);r=c.execute(q).fetchone();c.close()
        return (r[0] if r and r[0] is not None else d)
    except Exception: return d

def collect():
    DB="/opt/om-world/server/omw_server.db"
    since=int(time.time())-86400
    inv=_sql(DB,f"SELECT count(*) FROM invocations WHERE ts>{since}")
    drep=_sql(DB,f"SELECT count(*) FROM invocations WHERE pattern_id='meta-daily-report' AND ts>{since}")
    ob=0
    try: ob=sum(1 for _ in open("/opt/om-world/runtime/_outbox.jsonl"))
    except Exception: pass
    did=[f"飞轮今日 invocation {inv} 条", f"收到 daily_report {drep} 份"]
    bl=[f"outbox 积压 {ob}"] if ob>50 else []
    return _wrap(did,{"invocations_24h":inv,"daily_reports":drep,"outbox":ob},blockers=bl)

def _wrap(did,metrics,status="active",blockers=None,highlights=None):
    return {"schema":1,"project_id":PROJECT_ID,"date":TODAY,"did":did or ["今日无自动活动"],
            "metrics":metrics or {},"status":status,"blockers":blockers or [],"highlights":highlights or []}
if __name__=="__main__":
    rep=collect()
    print(json.dumps(rep,ensure_ascii=False,indent=(2 if "--dry" in sys.argv else None)))
