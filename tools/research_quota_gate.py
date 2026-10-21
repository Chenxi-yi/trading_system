"""Evaluate stdin quota JSON; save only a sanitized decision under ignored runtime."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.research.quota_policy import quota_decision


def main():
    decision=quota_decision(json.load(sys.stdin),int(time.time()*1000))
    out=ROOT/'runtime/research-loop/quota-decision.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(decision,ensure_ascii=False,indent=2)+'\n');out.chmod(0o600)
    print(json.dumps(decision,ensure_ascii=False))

if __name__=='__main__':main()
