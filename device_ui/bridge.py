"""Loopback-only USB bridge for the on-device R1-S3 test panel (no fake data)."""
import argparse
import hmac
import json
import secrets
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import serial

ROOT=Path(__file__).resolve().parents[1]
SESSION=ROOT/'data/device-panel/session.json'

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
            self.counter=(self.counter+1)&0xffffffff
            prefix=f'PANEL {self.counter} '
            self.serial.reset_input_buffer()
            self.serial.write((prefix+command+'\n').encode('ascii'))
            deadline=time.monotonic()+11
            while time.monotonic()<deadline:
                line=self.serial.readline(8192).decode('utf8',errors='replace').strip()
                if line.startswith(prefix):
                    return json.loads(line[len(prefix):])
            raise TimeoutError('Логер не відповів. Перевір прошивку v0.14+ і COM-порт; не повторюй запис без перевірки стану.')
        except Exception:
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
        elif path=='/api/state':
            try:
                state=self.server.device.request('STATE')
                state['transport']='usb'
                self.send_json(200,state)
            except Exception as e:self.send_json(503,dict(message=str(e)))
        else:self.send_json(404,dict(message='Not found'))
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
