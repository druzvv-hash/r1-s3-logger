"""R1-S3 configuration profiles over UART: explicit draft/apply/save, JSON on host."""
import argparse,hashlib,json,time,zlib
from pathlib import Path
import serial
import contracts as c
from backup_eeprom import capture
class Link:
 def __init__(self,port):
  self.port=serial.Serial(port=None,baudrate=115200,timeout=.3);self.port.dtr=False;self.port.rts=False;self.port.port=port;self.port.open();self.port.reset_input_buffer()
 def close(self):self.port.close()
 def lines(self,seconds=15):
  deadline=time.monotonic()+seconds
  while time.monotonic()<deadline:
   line=self.port.readline().decode('utf8',errors='replace').strip()
   if line.startswith('CONFIG ERROR'):raise ValueError(line)
   if line.startswith('CONFIG '):yield line
  raise TimeoutError('No complete configuration response')
 def command(self,command,expected):
  self.port.write((command+'\n').encode())
  for line in self.lines():
   if line.startswith(expected):return line
 def status(self):return self.command('CONFIG STATUS','CONFIG STATUS ')
 def fetch(self,source='applied'):
  self.port.write(({'applied':'CONFIG GET','draft':'CONFIG DRAFT','persisted':'CONFIG PERSISTED'}[source]+'\n').encode());data=bytearray();size=None;sha=None
  for line in self.lines():
   if line.startswith('CONFIG BEGIN '):
    _,_,n,sha=line.split();size=int(n)
    if not 0<size<=1472:raise ValueError('Invalid payload size')
   elif line.startswith('CONFIG HEX '):
    _,_,offset,raw=line.split()
    if int(offset,16)!=len(data) or size is None:raise ValueError('Chunk sequence')
    data.extend(bytes.fromhex(raw))
    if len(data)>size:raise ValueError('Oversized payload')
   elif line=='CONFIG END':
    if len(data)!=size or hashlib.sha256(data).hexdigest()!=sha:raise ValueError('Export hash mismatch')
    return c.decode_payload(data)
 def draft(self,values):
  payload=c.encode_payload(values);self.command(f'CONFIG BEGIN {len(payload)}','CONFIG OK BEGIN')
  for offset in range(0,len(payload),32):self.command(f'CONFIG HEX {offset:04X} {payload[offset:offset+32].hex()}','CONFIG OK HEX')
  self.command(f'CONFIG END {zlib.crc32(payload):08X}','CONFIG OK DRAFT')
  if c.encode_payload(self.fetch('draft'))!=payload:raise ValueError('Draft readback mismatch')
 def backup(self,path):
  if path.exists():raise ValueError('Backup path already exists')
  first=capture(self.port);second=capture(self.port)
  if first!=second:raise ValueError('Backup reads disagree')
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb') as stream:stream.write(first)
  with path.with_suffix('.json').open('x',encoding='utf8') as stream:json.dump(dict(bytes=4096,sha256=hashlib.sha256(first).hexdigest(),crc32=f'{zlib.crc32(first):08X}',matching_dumps=2),stream,indent=2)
  return first

def read_profile(path):
 obj=c.strict_json(path.read_bytes())
 if type(obj)!=dict or set(obj)!={'schema','major','minor','values'} or obj['schema']!='r1s3-config' or type(obj['major']) is not int or type(obj['minor']) is not int or obj['major']!=1 or obj['minor'] not in (0,1):raise ValueError('Unsupported configuration envelope')
 c.validate_config(obj['values'])
 if obj['minor']<c.config_minor(obj['values']):raise ValueError('Extended values require profile 1.1')
 return obj['values']
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',default='COM5');subs=parser.add_subparsers(dest='cmd',required=True)
 export=subs.add_parser('export');export.add_argument('path',type=Path);export.add_argument('--source',choices=['applied','draft','persisted'],default='applied')
 imp=subs.add_parser('import');imp.add_argument('path',type=Path)
 subs.add_parser('status');subs.add_parser('apply');subs.add_parser('defaults')
 save=subs.add_parser('save');save.add_argument('--backup',type=Path,help='New private backup path; defaults to Documents/R1-S3 Backups')
 args=parser.parse_args();values=read_profile(args.path) if args.cmd=='import' else None
 link=Link(args.port)
 try:
  if args.cmd=='export':
   values=link.fetch(args.source);obj=dict(schema='r1s3-config',major=1,minor=c.config_minor(values),values=values)
   with args.path.open('x',encoding='utf8') as stream:json.dump(obj,stream,indent=2,ensure_ascii=False)
   print(f'Exported {args.source}: {args.path}')
  elif args.cmd=='import':
   old=link.fetch();print(json.dumps({k:dict(applied=old[k],draft=v) for k,v in values.items() if old[k]!=v},indent=2,ensure_ascii=True));link.draft(values);print('Draft verified. Use apply, then explicit save.')
  elif args.cmd=='apply':print(link.command('CONFIG APPLY','CONFIG OK APPLY'))
  elif args.cmd=='defaults':print(link.command('CONFIG DEFAULTS','CONFIG OK DEFAULTS'))
  elif args.cmd=='save':
   path=args.backup or Path.home()/'Documents'/'R1-S3 Backups'/('before-save-'+time.strftime('%Y%m%d-%H%M%S')+'.bin')
   if path.with_suffix('.json').exists():raise ValueError('Backup manifest already exists')
   link.backup(path);print(f'Verified EEPROM backup: {path}');print(link.command('CONFIG SAVE','CONFIG OK SAVE'))
   if c.encode_payload(link.fetch())!=c.encode_payload(link.fetch('persisted')):raise ValueError('Persisted readback differs')
  print(link.status())
 finally:link.close()
if __name__=='__main__':main()
