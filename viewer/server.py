"""Run the private, local-only R1 viewer. Python 3.10+, no packages required."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
import tempfile
import threading
from urllib.parse import urlsplit, parse_qs, unquote
import webbrowser

from core import load, MappingRequired, MAX_FILE


class LimitedReader:
    def __init__(self, stream, size):
        self.stream,self.remaining=stream,size

    def readline(self, limit):
        if not self.remaining: return b''
        raw=self.stream.readline(min(limit,self.remaining))
        if not raw: raise ValueError('Upload ended before Content-Length')
        self.remaining-=len(raw)
        return raw


class App(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address):
        super().__init__(address,Handler)
        self.token=secrets.token_urlsafe(32)
        self.temp=tempfile.TemporaryDirectory(prefix='r1-viewer-')
        self.session=None
        self.lock=threading.Lock()

    def server_close(self):
        super().server_close()
        if self.session: self.session.close()
        self.temp.cleanup()


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass

    def respond(self,status,data,kind='application/json; charset=utf-8'):
        raw=json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf8') if kind.startswith('application/json') else data
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self,query):
        port=self.server.server_address[1]
        if self.headers.get('Host')!=f'127.0.0.1:{port}': return False
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://127.0.0.1:{port}': return False
        return secrets.compare_digest(self.headers.get('X-Viewer-Token',query.get('token',[''])[0]),self.server.token)

    def do_GET(self):
        url=urlsplit(self.path);query=parse_qs(url.query)
        if url.path in ('/style.css','/app.js'):
            name=url.path[1:]
            self.respond(200,(Path(__file__).parent/name).read_bytes(), 'text/css' if name.endswith('css') else 'text/javascript')
            return
        if not self.authorized(query):
            self.respond(403,dict(error='Open the address printed by the viewer launcher.'));return
        if url.path=='/':
            html=(Path(__file__).parent/'index.html').read_text(encoding='utf8').replace('__TOKEN__',self.server.token)
            self.respond(200,html.encode('utf8'),'text/html; charset=utf-8');return
        with self.server.lock:
            try:
                session=self.server.session
                if not session: raise ValueError('Choose a recording first')
                if url.path=='/api/summary': self.respond(200,session.summary)
                elif url.path=='/api/sample':
                    self.respond(200,session.sample(int(query.get('segment',['0'])[0]),float(query['seconds'][0])))
                elif url.path=='/api/window':
                    self.respond(200,session.window(int(query.get('segment',['0'])[0]),float(query['start'][0]),float(query['end'][0]),query.get('channels',['I_A,U_V'])[0].split(','),int(query.get('pixels',['1000'])[0])))
                else: self.respond(404,dict(error='Not found'))
            except (ValueError,KeyError,TypeError,OverflowError) as exc:
                self.respond(400,dict(error=str(exc)))

    def do_POST(self):
        url=urlsplit(self.path)
        if url.path!='/api/load' or not self.authorized(parse_qs(url.query)):
            self.respond(403,dict(error='Unauthorized local request'));return
        self.close_connection=True
        try:
            self.connection.settimeout(30)
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=MAX_FILE: raise ValueError('Choose a nonempty file up to 1 GiB')
            options=json.loads(self.headers.get('X-Viewer-Options','{}'))
            name=unquote(self.headers.get('X-Viewer-Name','recording'))[:200]
            if type(options) is not dict: raise ValueError('Invalid import options')
            with self.server.lock:
                database=Path(self.server.temp.name)/(secrets.token_hex(12)+'.sqlite')
                try:
                    new=load(LimitedReader(self.rfile,size),database,options)
                except Exception:
                    database.unlink(missing_ok=True)
                    raise
                new.summary['filename']=name
                old=self.server.session
                self.server.session=new
                if old:
                    oldpath=old.db.execute('PRAGMA database_list').fetchone()[2]
                    old.close(); Path(oldpath).unlink(missing_ok=True)
                self.respond(200,new.summary)
        except MappingRequired as exc:
            self.respond(422,dict(error=str(exc),preview=exc.preview,mapping_required=True))
        except (ValueError,TypeError,KeyError,UnicodeError,OverflowError,RecursionError) as exc:
            self.respond(400,dict(error=str(exc)))
        except (OSError,sqlite3.Error):
            self.respond(500,dict(error='Local disk/upload failure; source file was not changed'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    with App(('127.0.0.1',args.port)) as app:
        address=f'http://127.0.0.1:{app.server_address[1]}/?token={app.token}'
        print(address,flush=True)
        if not args.no_browser: webbrowser.open(address)
        try: app.serve_forever()
        except KeyboardInterrupt: pass


if __name__=='__main__': main()
