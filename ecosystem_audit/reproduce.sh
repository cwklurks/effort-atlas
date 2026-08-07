#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
command -v uv >/dev/null
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
python3 - <<'PY'
import json, subprocess
from pathlib import Path
root=Path.cwd();audit=root/'ecosystem_audit';repos=audit/'_repos';repos.mkdir(exist_ok=True)
for entry in json.loads((audit/'repos.lock.json').read_text())['repositories']:
    path=repos/entry['name']
    if not path.exists():
        subprocess.run(['git','clone','--no-checkout',entry['canonical_remote'],str(path)],check=True,env={**__import__('os').environ,'GIT_LFS_SKIP_SMUDGE':'1'})
    subprocess.run(['git','-C',str(path),'checkout','--detach',entry['sha']],check=True)
PY
python3 - <<'PY'
import json, subprocess
from pathlib import Path
pipelines=json.loads(Path('ecosystem_audit/adapter_manifest.json').read_text())['pipelines']
seen=set()
for pipeline in pipelines:
    command=pipeline['environment']['install_command']
    if command not in seen:
        subprocess.run(command,shell=True,check=True);seen.add(command)
PY
# Reconstruct ignored, metadata-only root test inputs from committed preflight schedules.
python3 - <<'PY'
import json
from pathlib import Path
root=Path.cwd();items={}
for path in (root/'confirmatory_artifacts/preflight-2026-07-22').glob('*_schedule.json'):
    for job in json.loads(path.read_text())['jobs']:
        items[job['item_id']]=job['domain']
data=root/'data';data.mkdir(exist_ok=True)
for domain in ('math','extraction'):
    selected=sorted((item,value) for item,value in items.items() if value==domain)
    (data/f'{domain}.jsonl').write_text(''.join(json.dumps({'id':item,'domain':value},sort_keys=True)+'\n' for item,value in selected))
PY
PYTHONPATH=trunccheck/src .venv/bin/python -m unittest discover -s trunccheck/tests -v
.venv/bin/python ecosystem_audit/run_executable_audit.py --locked --seed 1729 --check
.venv/bin/python ecosystem_audit/verify.py --strict
MPLCONFIGDIR=/tmp/effort-atlas-mpl PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
