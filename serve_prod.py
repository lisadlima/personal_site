import os, sys
os.chdir('/app/data/AUTORUN')
sys.path.insert(0, '/app/data/AUTORUN')
from fastcore.nbio import read_nb
nb = read_nb('/app/data/AUTORUN/app.ipynb')
ns = {}
for c in nb.cells:
    if c.cell_type != 'code': continue
    src = c.source
    if 'JupyUvi' in src or 'eval: false' in src: continue
    exec(src, ns)
import uvicorn
uvicorn.run(ns['app'], host='0.0.0.0', port=8000, log_level='warning')
