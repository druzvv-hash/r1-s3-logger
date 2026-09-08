"""Create a reproducible offline viewer source bundle; no runtime download."""
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['viewer/core.py','viewer/server.py','viewer/index.html','viewer/style.css','viewer/app.js','viewer/start.cmd','viewer/README.md',
       'tools/contracts.py','tools/make_contract_fixtures.py','tools/benchmark_viewer.py','tools/package_viewer.py',
       'tests/test_contracts.py','tests/test_viewer.py','tests/smoke_viewer.cjs','tests/r5_viewer.cjs',
       'schemas/config-v1.json','docs/CONFIG_SCHEMA.md','docs/FILE_FORMAT.md','docs/VIEWER_COMPATIBILITY.md','docs/P2_VIEWER.md','docs/R5_FEATURE_MIGRATION.md']


def main():
    out=ROOT/'.pio/r1-s3-viewer-0.2.zip';out.parent.mkdir(exist_ok=True)
    files={name:(ROOT/name).read_bytes().replace(b'\r\n',b'\n') for name in FILES}
    files['README.txt']=b'R1 / R1-S3 offline viewer 0.2\n\nRequires Python 3.10+ (no extra packages).\nUnzip, then open viewer/start.cmd on Windows, or run:\npython viewer/server.py\n\nSee viewer/README.md. This is a local application, not a standalone HTML file.\n'
    # Include exact-byte golden examples for offline inspection; never personal data.
    for path in (ROOT/'tests/fixtures').iterdir():
        if path.is_file():files[path.relative_to(ROOT).as_posix()]=path.read_bytes()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in sorted(files.items()):
            info=zipfile.ZipInfo('r1-s3-viewer/'+name,(2026,9,7,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,raw)
    print(out)


if __name__=='__main__':main()
