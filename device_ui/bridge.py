"""Loopback-only USB bridge for the on-device R1-S3 test panel (no fake data)."""
import argparse
import binascii
import hmac
import json
import logging
from logging.handlers import RotatingFileHandler
import secrets
import socket
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import serial

ROOT=Path(__file__).resolve().parents[1]
SESSION=ROOT/'data/device-panel/session.json'

def diagnostic(message):
    # Private bounded evidence for UART failures/reboots; never written to public docs.
    logger=logging.getLogger('r1.serial')
    if not logger.handlers:
        SESSION.parent.mkdir(parents=True,exist_ok=True)
        handler=RotatingFileHandler(SESSION.parent/'serial-diagnostic.log',maxBytes=2*1024*1024,backupCount=2,encoding='utf8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        logger.addHandler(handler);logger.setLevel(logging.INFO);logger.propagate=False
    logger.info(message)

def diagnostic_lines(raw):
    for line in raw.splitlines():
        if line and not line.startswith('PANEL '):diagnostic(line[:2000])

def file_path(hex_path):
    if not hex_path or len(hex_path)%2 or len(hex_path)>=480 or any(c not in '0123456789abcdefABCDEF' for c in hex_path):
        raise ValueError('Invalid SD path')
    raw=bytes.fromhex(hex_path)
    if not raw.startswith(b'/') or any(c<32 or c==127 for c in raw) or b'\\' in raw or b':' in raw:
        raise ValueError('Invalid SD path')
    if raw!=b'/' and any(p in (b'',b'.',b'..') for p in raw[1:].split(b'/')):
        raise ValueError('Invalid SD path')
    return raw

def file_command(text):
    parts=text.split(' ')
    if len(parts)==2 and parts[0] in ('LIST','OPEN'):
        file_path(parts[1])
    elif len(parts)==(3 if parts[0]=='READ' else 2) and parts[0] in ('READ','NEXT','CLOSE'):
        if not all(p.isascii() and p.isdecimal() and len(p)<=10 and int(p)<=0xffffffff for p in parts[1:]):
            raise ValueError('Invalid SD cursor')
    else:raise ValueError('Invalid SD command')
    return 'FILES '+text

def file_reply(device,command):
    result=device.request(file_command(command))
    if result.get('ok') is not True:raise RuntimeError(result.get('message','SD file operation failed'))
    return result

def read_chunk(device,session,size,offset):
    reply=file_reply(device,f'READ {session} {offset}')
    if reply.get('session')!=session or reply.get('size')!=size or reply.get('offset')!=offset:
        raise ValueError('SD transfer identity or offset mismatch')
    data=bytes.fromhex(reply['hex'])
    if len(data)!=min(2048,size-offset) or binascii.crc32(data)!=reply.get('crc32'):
        raise ValueError('SD transfer CRC/length mismatch; download incomplete')
    return data

class Device:
    def __init__(self,port):
        self.name=port
        self.serial=None
        self.lock=threading.Lock()
        self.counter=secrets.randbelow(2**31)
        self.stopping=False
    def close(self):
        if self.serial:
            self.serial.close()
            self.serial=None
    def request(self,command):
        if not self.lock.acquire(timeout=2):
            raise TimeoutError('USB зайнятий іншою командою')
        try:
            if self.stopping:raise RuntimeError('USB bridge is stopping')
            if self.serial is None:
                link=serial.Serial(port=None,baudrate=115200,timeout=.5,write_timeout=3)
                link.dtr=False
                link.rts=False
                link.port=self.name
                try: link.open()
                except Exception:
                    link.close()
                    raise
                self.serial=link
                diagnostic('UART opened with DTR/RTS inactive')
            self.counter=(self.counter+1)&0xffffffff
            prefix=f'PANEL {self.counter} '
            if self.serial.in_waiting:
                diagnostic_lines(self.serial.read(self.serial.in_waiting).decode('utf8',errors='replace'))
            self.serial.write((prefix+command+'\n').encode('ascii'))
            deadline=time.monotonic()+11
            while time.monotonic()<deadline:
                line=self.serial.readline(8192).decode('utf8',errors='replace').strip()
                if line.startswith(prefix):
                    return json.loads(line[len(prefix):])
                diagnostic_lines(line)
            raise TimeoutError('Логер не відповів. Перевір прошивку v0.14+ і COM-порт; не повторюй запис без перевірки стану.')
        except Exception as exc:
            diagnostic('UART request failed: '+str(exc))
            self.close()
            raise
        finally:
            self.lock.release()
    def stop(self):
        with self.lock:
            self.stopping=True
            self.close()

class PanelServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,device,token):
        self.device=device
        self.token=token
        super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass # URL contains the local session credential.
    def send_json(self,code,obj):
        self.respond(code,json.dumps(obj,ensure_ascii=False,allow_nan=False).encode('utf8'),'application/json; charset=utf-8')
    def respond(self,code,data,kind):
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass
    def authorized(self,post=False):
        port=self.server.server_port
        host=self.headers.get('Host','')
        if host not in (f'127.0.0.1:{port}',f'localhost:{port}'):return False
        token=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('token',[''])[0]
        if not hmac.compare_digest(token,self.server.token):return False
        if post and (self.headers.get('X-R1-Panel')!='1' or self.headers.get('Origin',f'http://{host}')!=f'http://{host}'):return False
        return True
    def do_GET(self):
        if not self.authorized():self.send_json(403,dict(message='Відкрий панель через start.cmd — потрібне актуальне посилання.'));return
        path=urllib.parse.urlsplit(self.path).path
        if path=='/':
            self.respond(200,(ROOT/'device_ui/index.html').read_bytes(),'text/html; charset=utf-8')
        elif path=='/api/live':
            after=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('after',['0'])[0]
            if not after.isascii() or not after.isdecimal() or len(after)>16 or int(after)>9007199254740991:
                self.send_json(400,dict(message='Invalid live cursor'));return
            try:self.send_json(200,self.server.device.request('LIVE '+after))
            except Exception as e:self.send_json(503,dict(message=str(e)))
        elif path=='/api/state':
            try:
                state=self.server.device.request('STATE')
                state['transport']='usb'
                self.send_json(200,state)
            except Exception as e:self.send_json(503,dict(message=str(e)))
        elif path=='/api/files':
            command=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('command',[''])[0]
            try:command=file_command(command)
            except ValueError as e:self.send_json(400,dict(message=str(e)));return
            try:self.send_json(200,self.server.device.request(command))
            except Exception as e:self.send_json(503,dict(message=str(e)))
        elif path=='/api/download':self.download()
        else:self.send_json(404,dict(message='Not found'))
    def download(self):
        path=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('path',[''])[0]
        try:raw=file_path(path)
        except ValueError as e:self.send_json(400,dict(message=str(e)));return
        session=None;started=False
        try:
            opened=file_reply(self.server.device,'OPEN '+path)
            session,size=opened['session'],opened['size']
            if type(session) is not int or not 0<session<=0xffffffff or type(size) is not int or not 0<=size<=0xffffffff:
                raise ValueError('Invalid SD file metadata')
            # Validate the first block before sending headers. Never buffer a whole recording.
            block=read_chunk(self.server.device,session,size,0)
            self.connection.settimeout(10)
            self.send_response(200)
            self.send_header('Content-Type','application/octet-stream')
            self.send_header('Content-Length',str(size))
            self.send_header('Content-Disposition',"attachment; filename=\"r1s3-download.bin\"; filename*=UTF-8''"+urllib.parse.quote_from_bytes(raw.rsplit(b'/',1)[-1],safe=''))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.end_headers();started=True
            offset=0
            while offset<size:
                self.wfile.write(block);offset+=len(block)
                if offset<size:block=read_chunk(self.server.device,session,size,offset)
        except Exception as e:
            if not started:self.send_json(503,dict(message=str(e)))
            else:
                # A short HTTP body must remain visibly incomplete, never a successful corrupt file.
                self.close_connection=True
                try:self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:pass
        finally:
            if session:
                try:file_reply(self.server.device,f'CLOSE {session}')
                except Exception:pass # Firmware also expires abandoned sessions after 30 seconds.
    def do_POST(self):
        if not self.authorized(post=True):self.send_json(403,dict(message='Origin/token/header rejected'));return
        path=urllib.parse.urlsplit(self.path).path
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:length=-1
        if length<0 or length>3099:
            self.close_connection=True;self.send_json(413,dict(message='Command too large'));return
        if path=='/api/shutdown':
            self.server.device.stop() # Reply only after pending I/O ended and COM was closed.
            self.send_json(200,dict(ok=True,message='USB-сервер зупиняється; COM-порт буде звільнено'))
            threading.Thread(target=self.server.shutdown,daemon=True).start()
            return
        if path!='/api/command':self.send_json(404,dict(message='Not found'));return
        self.connection.settimeout(5)
        try:
            body=self.rfile.read(length).decode('ascii')
            if len(body)!=length or not body or '\n' in body or '\r' in body or '\0' in body:raise ValueError('Invalid command')
            self.send_json(200,self.server.device.request('DO '+body))
        except Exception as e:self.send_json(503,dict(ok=False,message=str(e)))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',default='COM5')
    p.add_argument('--http-port',type=int,default=8767)
    p.add_argument('--open',action='store_true')
    p.add_argument('--stop',action='store_true')
    args=p.parse_args()
    if args.stop:
        if not SESSION.exists():
            print('No running USB panel session.')
            return
        info=json.loads(SESSION.read_text())
        url=info['url'].replace('/?','/api/shutdown?')
        request=urllib.request.Request(url,data=b'',headers={'X-R1-Panel':'1'},method='POST')
        with urllib.request.urlopen(request,timeout=15) as response:
            if not json.load(response).get('ok'):raise RuntimeError('Shutdown rejected')
        print('USB panel stopped; serial port released.')
        return
    if args.open and SESSION.exists():
        try:
            info=json.loads(SESSION.read_text())
            parsed=urllib.parse.urlsplit(info['url'])
            if parsed.scheme=='http' and parsed.hostname=='127.0.0.1' and parsed.port==args.http_port and info['port']==args.port:
                with urllib.request.urlopen(info['url'],timeout=2) as response:
                    if response.status==200:
                        import webbrowser
                        webbrowser.open(info['url'])
                        print('Opened the running USB panel.')
                        return
        except (OSError,ValueError,KeyError):pass
    token=secrets.token_urlsafe(32)
    device=Device(args.port)
    server=PanelServer(('127.0.0.1',args.http_port),device,token)
    url=f'http://127.0.0.1:{server.server_port}/?token={token}'
    SESSION.parent.mkdir(parents=True,exist_ok=True)
    SESSION.write_text(json.dumps(dict(url=url,port=args.port)),encoding='utf8')
    print(f'R1-S3 USB panel ({args.port}): {url}',flush=True)
    print('Before uploading firmware: run device_ui/stop.cmd to release the serial port.',flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        server.server_close()
        with device.lock:device.close()
        if SESSION.exists() and json.loads(SESSION.read_text()).get('url')==url:SESSION.unlink()
if __name__=='__main__':main()
