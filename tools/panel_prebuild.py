"""PlatformIO hook: regenerate embedded assets before each build."""
Import("env")
import runpy
runpy.run_path(env.subst("$PROJECT_DIR")+"/tools/build_panel.py")["build"]()
import subprocess,json
from pathlib import Path
root=Path(env.subst("$PROJECT_DIR"))
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip())
provenance='#pragma once\n#define R1_BUILD_COMMIT '+json.dumps(commit)+'\n#define R1_BUILD_DIRTY '+('true' if dirty else 'false')+'\n'
path=root/'firmware/include/build_provenance.h'
if not path.exists() or path.read_text()!=provenance:path.write_text(provenance,encoding='utf8')
