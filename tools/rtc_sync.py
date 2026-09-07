"""Local browser-to-UART RTC synchronization for HWTEST v0.7.
Run with PlatformIO's Python (pyserial required); bind to loopback only.
"""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import serial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial-port', default='COM5')
    parser.add_argument('--http-port', type=int, default=8765)
    args = parser.parse_args()
    origin = f'http://127.0.0.1:{args.http_port}'

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, payload):
            data = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path != '/':
                self.send_error(404)
                return
            data = Path(__file__).with_name('rtc-sync.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if (self.path != '/sync' or self.headers.get('Origin') != origin
                    or self.headers.get('Host') != f'127.0.0.1:{args.http_port}'
                    or self.headers.get('Content-Type') != 'application/json'):
                self.send_error(403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 256:
                    raise ValueError('Invalid request size')
                body = json.loads(self.rfile.read(length))
                browser_ms = body['browserMs']
                if type(browser_ms) is not int or not 946684800000 <= browser_ms < 4102444798000:
                    raise ValueError('Browser date must be in 2000–2099')
                received = time.monotonic()
                # Open without asserting modem control lines. Driver opening transients may still occur.
                with serial.Serial(port=None, baudrate=115200, timeout=0.5) as uart:
                    uart.dtr = False
                    uart.rts = False
                    uart.port = args.serial_port
                    uart.open()
                    # Compensate only local processing delay, using the browser as clock source.
                    epoch = (browser_ms + int((time.monotonic() - received) * 1000)) // 1000
                    uart.write(f'TIME UTC {epoch}\n'.encode('ascii'))
                    uart.flush()
                    deadline = time.monotonic() + 18
                    lines = []
                    while time.monotonic() < deadline:
                        line = uart.readline().decode('utf-8', errors='replace').strip()
                        if not line:
                            continue
                        lines.append(line)
                        if line.startswith(f'RTC SET OK UTC {epoch}:'):
                            self.reply(200, {'ok': True, 'epoch': epoch, 'message': line})
                            return
                        if line.startswith('RTC SET ERROR:'):
                            raise RuntimeError(line)
                    raise RuntimeError('No RTC acknowledgement. Check HWTEST v0.7 and close other serial monitors. ' + ' | '.join(lines[-3:]))
            except (ValueError, KeyError, RuntimeError, serial.SerialException, OSError) as exc:
                self.reply(400, {'ok': False, 'message': str(exc)})

    print(f'Open {origin} in a browser; serial port {args.serial_port}. Ctrl+C stops the helper.', flush=True)
    HTTPServer(('127.0.0.1', args.http_port), Handler).serve_forever()


if __name__ == '__main__':
    main()
