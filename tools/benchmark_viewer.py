"""Generate a private temporary native file and benchmark the streaming viewer."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import tracemalloc
import zlib
import contracts as c
from make_contract_fixtures import metadata

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from core import load


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows',type=int,default=250000)
    args=parser.parse_args()
    if not 1<=args.rows<=1000000:parser.error('rows must be 1..1000000')
    with tempfile.TemporaryDirectory(prefix='r1-viewer-benchmark-') as temp:
        source=Path(temp)/'synthetic.csv'
        with source.open('wb') as stream:
            digest=hashlib.sha256()
            def write(raw):stream.write(raw);digest.update(raw)
            metaraw=b'# META '+c.canonical(metadata())+b'\n'
            write(c.MAGIC+metaraw+f'# META_CRC32 {c.crc(metaraw):08X}\n'.encode()+(','.join(c.COLUMNS)+'\n').encode())
            for base in range(0,args.rows,256):
                count=min(256,args.rows-base);start=stream.tell();checksum=0
                for seq in range(base,base+count):
                    raw=f',{seq*20},0,5,0,0,0,0,{seq},{seq*20000},0,25600,3200,8,0,0,0\n'.encode()
                    checksum=zlib.crc32(raw,checksum);write(raw)
                cp=dict(start=start,end=stream.tell(),rows=count,first_seq=base,last_seq=base+count-1,crc32=f'{checksum:08X}')
                write(b'# CHECKPOINT '+c.canonical(cp)+b'\n')
            stream.write(b'# END '+c.canonical(dict(rows=args.rows,sha256=digest.hexdigest(),clean=True,reason='stop'))+b'\n')
        tracemalloc.start();begin=time.perf_counter()
        with source.open('rb') as stream:session=load(stream,Path(temp)/'index.db')
        imported=time.perf_counter()-begin;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        begin=time.perf_counter()
        result=session.window(0,0,(args.rows-1)*.02,['I_A','P_W'],1000)
        queried=time.perf_counter()-begin
        assert session.summary['rows']==args.rows and session.summary['integrity']=='verified clean'
        assert result['stats']['I_A']['count']==args.rows
        print(json.dumps(dict(rows=args.rows,bytes=source.stat().st_size,import_seconds=round(imported,3),window_seconds=round(queried,3),python_traced_peak_bytes=peak,envelope_bins=len(result['envelopes']['I_A']),database_bytes=(Path(temp)/'index.db').stat().st_size),indent=2))
        session.close()


if __name__=='__main__':main()
