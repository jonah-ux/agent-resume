import json,tempfile,pathlib
from agent_resume.cli import main
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/'resume.json'; p.write_text(json.dumps({'schema':'agent-resume/v1','goal':'ship demo','repository':'demo','commit':'abc123'}))
 print('Agent Resume demo: continue with identity attached')
 main(['validate',str(p)])
