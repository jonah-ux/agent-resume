import argparse,json,pathlib

def main(argv=None):
 p=argparse.ArgumentParser(prog='agent-resume'); p.add_argument('command',choices=['create','inspect','validate','render']); p.add_argument('path',nargs='?'); p.add_argument('--out',default='resume.json'); a=p.parse_args(argv)
 if a.command=='create':
  d={'schema':'agent-resume/v1','goal':'','repository':'','branch':'','commit':'','completed':[],'pending':[],'evidence':[],'unknowns':[]}; pathlib.Path(a.out).write_text(json.dumps(d,indent=2)+'\n'); print(json.dumps(d,indent=2)); return 0
 d=json.load(open(a.path or a.out)); ok=d.get('schema')=='agent-resume/v1' and bool(d.get('goal')) and bool(d.get('repository')) and bool(d.get('commit')); print(json.dumps({'schema':'agent-resume/validation/v1','ok':ok,'reason':'goal, repository, and commit are required' if not ok else 'valid'},indent=2)); return 0 if ok else 1
