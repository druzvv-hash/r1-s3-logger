"""Compare all copper/mechanical/footprint S-expressions to pre-logo Git HEAD."""
from pathlib import Path
import subprocess,re,collections,json,hashlib
root=Path(__file__).resolve().parents[1]
path='hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'
old=subprocess.check_output(['git','show','HEAD:'+path],cwd=root).decode()
new=(root/'R3_power.kicad_pcb').read_text(encoding='utf-8')
def blocks(text):
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',text)
    depth=0; start=0; out=[]
    for i,t in enumerate(tokens):
        if t=='(':
            depth+=1
            if depth==2: start=i
        elif t==')':
            if depth==2: out.append(tuple(tokens[start:i+1]))
            depth-=1
    return out
a=collections.Counter(blocks(old)); b=collections.Counter(blocks(new))
removed=list((a-b).elements()); added=list((b-a).elements())
allowed={'gr_poly','gr_line','gr_circle','gr_text','group'}
assert not removed,[(x[1],x[:10]) for x in removed]
assert all(x[1] in allowed for x in added)
assert all('"F.SilkS"' in x for x in added if x[1]!='group')
report={'baseline':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
 'board_sha256':hashlib.sha256((root/'R3_power.kicad_pcb').read_bytes()).hexdigest(),
 'existing_board_records_unchanged':True,'added_records':dict(collections.Counter(x[1] for x in added))}
(root/'reports/branding_invariants.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
