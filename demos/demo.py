import tempfile,pathlib
from agent_resume.cli import main
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/'resume.json'
 print('Agent Resume demo: create and validate an integrity-bound handoff')
 main(['create','--out',str(p),'--goal','ship demo','--repository','demo','--branch','main','--commit','abc123'])
 main(['validate',str(p),'--require-fingerprint'])
 main(['inspect',str(p),'--require-fingerprint'])
