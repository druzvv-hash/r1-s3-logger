"""Bounded, opt-in overnight UART/SD endurance run; no Flash/EEPROM writes.

Shares one UART owner with a read-only live panel during the run. A stop file or
authenticated POST /api/overnight-stop requests orderly cleanup. The panel stays
available after completion. Private artifacts go exclusively below data/.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'device_ui'), str(ROOT / 'tools'), str(ROOT / 'viewer')]
import bridge
import contracts

SAFE_FIELDS = ('firmware', 'boot', 'revision', 'reset_reason', 'uptime_ms',
    'sample_id', 'valid_samples', 'invalid_samples', 'missed_samples',
    'requested_hz', 'measured_hz', 'i2c_hz', 'i2c_errors', 'heap_free',
    'psram_free', 'queue_bytes', 'sd_block_bytes', 'oled_frames', 'oled_chunk_us',
    'max_late_us', 'max_read_us', 'preview_drops', 'maintenance_count',
    'recording_state', 'recording_path', 'recording_error', 'recording_rows',
    'recording_bytes', 'recording_queued', 'recording_high_water',
    'recording_overflows', 'recording_write_us', 'recording_sync_us',
    'recording_part', 'file_transfer', 'generation', 'settings_status',
    'volts', 'amps', 'temp_c', 'rtc', 'utc', 'ap_clients')


def utc():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf8')
    os.replace(temporary, path)


def validate_record(path):
    """Production streaming decoder: metadata/checkpoints/END/semantics + cadence."""
    import core
    database = path.with_suffix('.validation.sqlite')
    with path.open('rb') as source:
        session = core.load(source, database)
    try:
        s = session.summary
        if s['integrity'] != 'verified clean' or s['unverified_rows'] or s['partial_line']:
            raise ValueError('Recording is not completely verified and clean')
        missing = gaps = 0
        first = previous = None
        intervals = {'min': None, 'max': 0, 'sum': 0, 'count': 0}
        channels = {k: {'count': 0, 'mean': 0., 'm2': 0., 'min': None, 'max': None}
                    for k in ('U_V', 'I_A')}
        for (payload,) in session.db.execute('SELECT payload FROM samples ORDER BY n'):
            r = json.loads(payload)
            seq, tus = int(r['seq']), int(r['t_us'])
            if first is None:
                first = r
            if previous is not None:
                missing += seq - int(previous['seq']) - 1
                dt = tus - int(previous['t_us'])
                intervals['min'] = dt if intervals['min'] is None else min(dt, intervals['min'])
                intervals['max'] = max(dt, intervals['max'])
                intervals['sum'] += dt
                intervals['count'] += 1
            gaps += bool(r['quality'] & contracts.GAP)
            for k, c in channels.items():
                v = r[k]
                if v is None:
                    continue
                c['count'] += 1
                delta = v - c['mean']
                c['mean'] += delta / c['count']
                c['m2'] += delta * (v - c['mean'])
                c['min'] = v if c['min'] is None else min(v, c['min'])
                c['max'] = v if c['max'] is None else max(v, c['max'])
            previous = r
        for c in channels.values():
            c['std'] = (c.pop('m2') / c['count']) ** .5 if c['count'] else None
        result = dict(file=path.name, bytes=path.stat().st_size, rows=s['rows'],
                      integrity=s['integrity'], invalid_rows=s['invalid_rows'],
                      missing_sequences=missing, gap_rows=gaps, channels=channels,
                      requested_hz=s['metadata']['config']['requested_rate_hz'],
                      interval_us=intervals, writer=s['metadata']['writer'])
        result['actual_hz'] = (1e6 * intervals['count'] / intervals['sum']
                               if intervals['sum'] else None)
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        result['sha256'] = digest.hexdigest()
        # The independent whole-file oracle deliberately caps input at 16 MiB.
        if path.stat().st_size <= 16 * 1024 * 1024:
            reference = contracts.read_native(path.read_bytes())
            if not reference['clean'] or len(reference['rows']) != s['rows']:
                raise ValueError('Reference decoder disagrees with streaming decoder')
            result['reference_rows'] = len(reference['rows'])
        if not s['rows'] or s['invalid_rows'] or missing or gaps:
            raise ValueError('Recording contains missing/invalid/gap rows or is empty')
        return result
    finally:
        session.close()


class Endurance:
    def __init__(self, device, out, baseline, hours):
        self.device, self.out, self.baseline = device, out, baseline
        self.stop = threading.Event()
        self.active = True
        self.started = time.monotonic()
        self.deadline = self.started + hours * 3600
        self.expected = baseline['config_hex']
        self.last_state = None
        self.measure_base = None
        self.record_path = None
        self.start_pending = False
        self.file_session = None
        self.driver_errors = []
        self.requests = self.request_errors = 0
        self.stats_lock = threading.Lock()
        self.status = dict(status='running', phase='canary', started_utc=utc(),
            expected_end_utc=datetime.fromtimestamp(time.time() + hours * 3600,
                                                    timezone.utc).isoformat(),
            pid=os.getpid(), hours=hours, conditions='PSU OFF, wires connected',
            plan=[{'hz': hz, 'record_seconds': 1200} for hz in (50, 100, 300)],
            records=[], errors=[], baseline={k: baseline.get(k) for k in SAFE_FIELDS})
        self.events = logging.getLogger('overnight.events')
        self.events.setLevel(logging.INFO)
        self.events.propagate = False
        handler = RotatingFileHandler(out / 'events.jsonl', maxBytes=8*1024*1024,
                                      backupCount=3, encoding='utf8')
        self.events.addHandler(handler)

    def publish(self):
        with self.stats_lock:
            self.status.update(updated_utc=utc(), elapsed_s=round(time.monotonic()-self.started, 1),
                               requests=self.requests, request_errors=self.request_errors,
                               uart_error_events=len(self.driver_errors))
            atomic_json(self.out / 'status.json', self.status)

    def event(self, kind, **data):
        self.events.info(json.dumps(dict(time=utc(), kind=kind, **data)))

    def check_stop(self):
        if self.stop.is_set() or (self.out / 'STOP').exists():
            raise InterruptedError('Owner requested orderly stop')
        if time.monotonic() >= self.deadline:
            raise TimeoutError('Night test time budget exhausted before this phase completed')
        if shutil.disk_usage(self.out).free < 2*1024**3:
            raise RuntimeError('PC disk reserve below 2 GiB')

    def raw_state(self):
        for attempt in range(3):
            try:
                return self.device.request('STATE')
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1)

    def state(self, enforce=True):
        s = self.raw_state()
        self.event('state', **{k: s.get(k) for k in SAFE_FIELDS})
        self.status['latest'] = {k: s.get(k) for k in SAFE_FIELDS}
        self.publish()
        if enforce:
            if s['boot'] != self.baseline['boot']:
                raise RuntimeError('Unexpected ESP32 reboot; no automatic reset will hide it')
            if s['generation'] != self.baseline['generation'] or s['config_hex'] != self.expected:
                raise RuntimeError('Unexpected configuration change')
            if self.last_state and (s['uptime_ms'] <= self.last_state['uptime_ms'] or
                                    s['sample_id'] <= self.last_state['sample_id']):
                raise RuntimeError('Uptime or acquisition stopped advancing')
            if self.measure_base and any(s[k] != self.measure_base[k]
                    for k in ('missed_samples', 'invalid_samples', 'i2c_errors')):
                raise RuntimeError('Acquisition/I2C error counter increased')
            if s['recording_state'] == 'ERROR' or s['recording_overflows']:
                raise RuntimeError('SD/FIFO error: ' + s.get('recording_error', ''))
            if self.driver_errors:
                raise RuntimeError('Windows reported a UART error flag')
            if s['heap_free'] < 20000 or s['psram_free'] < 1024*1024:
                raise RuntimeError('Device memory reserve exhausted')
        self.last_state = s
        return s

    def command(self, verb):
        s = self.raw_state()
        if s['boot'] != self.baseline['boot'] or s['generation'] != self.baseline['generation']:
            raise RuntimeError('Control identity/generation changed')
        # Never replay a state-changing command after an ambiguous reply.
        r = self.device.request(f"DO {s['boot']} {s['revision']} {verb}")
        if not r.get('ok'):
            raise RuntimeError(r.get('message', 'Command rejected'))
        return r

    def wait_state(self, target, seconds=20):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            time.sleep(.5)
            s = self.raw_state()
            if s['boot'] != self.baseline['boot']:
                raise RuntimeError('Unexpected reboot during state transition')
            if s['recording_state'] == 'ERROR':
                raise RuntimeError(s['recording_error'])
            if s['recording_state'] == target:
                return s
        raise TimeoutError('State transition did not reach ' + target)

    def apply_rate(self, hz):
        s = self.raw_state()
        if s['recording_state'] != 'READY' or s['file_transfer']:
            raise RuntimeError('Rate change requires idle storage')
        config = contracts.decode_payload(bytes.fromhex(self.baseline['config_hex']))
        js = "const fs=require('fs'),{configForRate}=require('./device_ui/rate_profile.js');process.stdout.write(JSON.stringify(configForRate(JSON.parse(fs.readFileSync(0,'utf8')),Number(process.argv[1]))));"
        config = json.loads(subprocess.check_output([str(Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'nodejs/node.exe'), '-e', js, str(hz)],
                    cwd=ROOT, input=json.dumps(config).encode(), timeout=10))
        # Keep a long run within one file; preserve the owner's chosen storage policy.
        if config['rotation_bytes'] < hz * 1200 * 512 + 100000:
            raise RuntimeError('Configured rotation too small for the planned single-part test')
        payload = contracts.encode_payload(config).hex()
        self.command('APPLY ' + payload)
        self.expected = payload
        time.sleep(1)
        self.last_state = None
        self.measure_base = None
        s = self.state()
        self.measure_base = s
        if s['requested_hz'] != hz:
            raise RuntimeError('Requested rate did not apply')

    def poll(self, seconds, recording=False):
        until = min(self.deadline, time.monotonic() + seconds)
        next_state = 0
        while time.monotonic() < until:
            self.check_stop()
            r = self.device.request('LIVE 0')
            if r['boot'] != self.baseline['boot']:
                raise RuntimeError('Live stream boot changed')
            if time.monotonic() >= next_state:
                s = self.state()
                if s['recording_state'] != ('RUNNING' if recording else 'READY'):
                    raise RuntimeError('Unexpected recording state during endurance phase')
                if recording and s['recording_path'] != self.record_path:
                    raise RuntimeError('Unexpected file rotation/path change')
                next_state = time.monotonic() + 5
            self.stop.wait(.5)

    def recording(self, hz, seconds):
        self.check_stop()
        self.status['phase'] = f'record_{hz}hz_{seconds}s'
        self.apply_rate(hz)
        self.start_pending = True
        self.command('START')
        s = self.wait_state('RUNNING')
        self.record_path = s['recording_path']
        self.start_pending = False
        self.poll(seconds, recording=True)
        self.command('STOP')
        s = self.wait_state('READY')
        expected_path = self.record_path.removesuffix('.part') + '.csv'
        if s['recording_path'] != expected_path or s['recording_part'] != 0:
            raise RuntimeError('Recording finalization/path mismatch')
        self.record_path = None
        record = dict(hz=hz, requested_seconds=seconds, path=expected_path,
                      saved_rows=s['recording_rows'], saved_bytes=s['recording_bytes'],
                      fifo_high_water=s['recording_high_water'],
                      write_us=s['recording_write_us'], sync_us=s['recording_sync_us'])
        self.status['records'].append(record)
        self.publish()
        self.download(record)

    def download(self, record):
        self.status['phase'] = 'download_' + str(record['hz']) + 'hz'
        opened = bridge.file_reply(self.device, 'OPEN ' + record['path'].encode().hex())
        self.file_session, size = opened['session'], opened['size']
        if size != record['saved_bytes']:
            raise ValueError('SD size differs from finalized recording byte count')
        path = self.out / Path(record['path']).name
        partial = path.with_suffix('.download')
        digest = hashlib.sha256()
        offset, next_state = 0, 0
        with partial.open('xb') as output:
            while offset < size:
                self.check_stop()
                block = bridge.read_chunk(self.device, self.file_session, size, offset)
                output.write(block)
                digest.update(block)
                offset += len(block)
                if time.monotonic() >= next_state:
                    record['downloaded_bytes'] = offset
                    self.state()
                    next_state = time.monotonic() + 5
        bridge.file_reply(self.device, f'CLOSE {self.file_session}')
        self.file_session = None
        partial.rename(path)
        record.update(downloaded_bytes=offset, transfer_sha256=digest.hexdigest())
        self.status['phase'] = 'validate_' + str(record['hz']) + 'hz'
        self.publish()
        result_path = path.with_suffix('.validation.json')
        with result_path.open('x', encoding='utf8') as output, path.with_suffix('.validation.err').open('x') as errors:
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--validate-file', str(path)],
                                     stdout=output, stderr=errors, cwd=ROOT,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                while child.poll() is None:
                    self.check_stop()
                    self.state()
                    self.stop.wait(5)
                if child.returncode:
                    raise RuntimeError('Downloaded file validation failed; inspect private validation.err')
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=10)
        result = json.loads(result_path.read_text())
        if result['sha256'] != record['transfer_sha256'] or result['rows'] != record['saved_rows'] or result['requested_hz'] != record['hz']:
            raise RuntimeError('Validated file differs from transfer/device metadata')
        record['validation'] = result
        self.publish()

    def cleanup(self):
        if self.file_session is not None:
            bridge.file_reply(self.device, f'CLOSE {self.file_session}')
            self.file_session = None
        s = self.raw_state()
        # Only stop a recording started by this runner, never an unrelated user session.
        if s['boot'] == self.baseline['boot'] and (self.record_path or self.start_pending):
            if s['recording_state'] == 'STARTING':
                s = self.wait_state('RUNNING')
            if s['recording_state'] == 'RUNNING':
                if self.record_path and s['recording_path'] != self.record_path:
                    raise RuntimeError('Cleanup refused to stop a different recording')
                self.command('STOP')
                s = self.wait_state('READY')
            elif s['recording_state'] == 'STOPPING':
                s = self.wait_state('READY')
        if s['recording_state'] != 'READY' or s['generation'] != self.baseline['generation']:
            raise RuntimeError('Cannot safely restore config in current device state')
        if s['config_hex'] not in (self.expected, self.baseline['config_hex']):
            raise RuntimeError('Configuration changed externally; baseline restoration skipped')
        if s['config_hex'] != self.baseline['config_hex']:
            # After a reboot, do not issue more controls automatically.
            self.command('APPLY ' + self.baseline['config_hex'])
            time.sleep(1)
        s = self.raw_state()
        if s['config_hex'] != self.baseline['config_hex'] or s['generation'] != self.baseline['generation']:
            raise RuntimeError('Restoration verification failed')
        atomic_json(self.out / 'restored.json', s)
        self.status['restored'] = {k: s.get(k) for k in SAFE_FIELDS}

    def run(self):
        # Temporary sleep inhibition, scoped to this test thread; no power-plan change.
        inhibitor = ctypes.windll.kernel32.SetThreadExecutionState
        self.status['sleep_inhibited'] = bool(inhibitor(0x80000001))
        try:
            self.recording(50, 5)
            self.status['canary_passed'] = True
            self.publish()
            for hz in (50, 100, 300):
                self.recording(hz, 1200)
            self.apply_rate(300)
            self.status['phase'] = 'continuous_300hz_until_deadline'
            self.poll(max(0, self.deadline-time.monotonic()-2))
            self.status['status'] = 'completed'
        except InterruptedError as exc:
            self.status.update(status='stopped', failure=str(exc))
        except Exception as exc:
            self.status.update(status='failed', failure=str(exc))
            self.event('failure', error=str(exc))
        finally:
            self.status['phase'] = 'cleanup'
            self.publish()
            try:
                self.cleanup()
            except Exception as exc:
                self.status['cleanup_error'] = str(exc)
                self.status['status'] = 'needs_attention'
            atomic_json(self.out / 'uart-errors.json', self.driver_errors)
            self.status.update(phase='finished', finished_utc=utc())
            self.active = False
            self.publish()
            inhibitor(0x80000000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hardware', action='store_true')
    parser.add_argument('--hours', type=float, default=10)
    parser.add_argument('--out')
    parser.add_argument('--validate-file', type=Path)
    args = parser.parse_args()
    if args.validate_file:
        print(json.dumps(validate_record(args.validate_file), indent=2))
        return
    if not args.hardware or not args.out or not 1 <= args.hours <= 12:
        parser.error('Use --hardware --out <new folder under data> --hours 1..12')
    out = Path(args.out).resolve()
    if not out.is_relative_to(ROOT / 'data'):
        parser.error('Output must be a new folder under repository data/')
    out.mkdir(parents=True, exist_ok=False)
    old = json.loads(bridge.SESSION.read_text())
    def old_api(route, body=None):
        request = urllib.request.Request(old['url'].replace('/?', route+'?'), data=body,
                                         headers={'X-R1-Panel': '1'})
        with urllib.request.urlopen(request, timeout=18) as response:
            return json.load(response)
    baseline = old_api('/api/state')
    if baseline['recording_state'] != 'READY' or baseline['file_transfer'] or not baseline['ready']:
        raise RuntimeError('Logger must be READY without an active transfer')
    atomic_json(out/'baseline.json', baseline)
    atomic_json(out/'manifest.json', dict(created_utc=utc(), hours=args.hours,
        port=old['port'], firmware=baseline['firmware'], conditions='PSU OFF, wires connected',
        no_flash_write=True, no_eeprom_save=True, no_reset=True))
    if not old_api('/api/shutdown', b'').get('ok'):
        raise RuntimeError('Existing bridge did not release UART')
    time.sleep(1)
    device = bridge.Device(old['port'])
    run = Endurance(device, out, baseline, args.hours)
    original_request = device.request
    def measured_request(command):
        began = time.monotonic()
        try:
            reply = original_request(command)
            with run.stats_lock:
                run.requests += 1
            run.event('request', command=command.split()[0], seconds=round(time.monotonic()-began, 4), ok=True)
            return reply
        except Exception as exc:
            with run.stats_lock:
                run.request_errors += 1
            run.event('request', command=command.split()[0], seconds=round(time.monotonic()-began, 4), ok=False, error=str(exc))
            raise
    device.request = measured_request
    from serial import win32
    original_clear = win32.ClearCommError
    def capture(handle, flags, stat):
        result = original_clear(handle, flags, stat)
        bits = ctypes.cast(flags, ctypes.POINTER(win32.DWORD)).contents.value
        if bits and run.active:
            event = dict(time=utc(), mask=bits)
            run.driver_errors.append(event)
            atomic_json(out/'uart-errors.json', run.driver_errors)
        return result
    win32.ClearCommError = capture

    class Handler(bridge.Handler):
        def do_POST(self):
            path = urllib.parse.urlsplit(self.path).path
            if path == '/api/overnight-stop':
                if not self.authorized(post=True):
                    self.send_json(403, dict(message='Unauthorized'))
                    return
                run.stop.set()
                self.send_json(200, dict(ok=True, message='Orderly night-test stop requested'))
            elif run.active:
                self.close_connection = True
                self.send_json(409, dict(message='Нічний тест триває. Керування тимчасово зайняте тестом.'))
            else:
                super().do_POST()
        def do_GET(self):
            path = urllib.parse.urlsplit(self.path).path
            if run.active and path in ('/api/files', '/api/download'):
                self.send_json(409, dict(message='microSD зайнята нічним тестом'))
            else:
                super().do_GET()

    port = urllib.parse.urlsplit(old['url']).port
    token = secrets.token_urlsafe(32)
    server = bridge.PanelServer(('127.0.0.1', port), device, token)
    server.RequestHandlerClass = Handler
    url = f'http://127.0.0.1:{port}/?token={token}'
    atomic_json(bridge.SESSION, dict(url=url, port=old['port']))
    run.publish()
    thread = threading.Thread(target=run.run, name='overnight-test', daemon=False)
    thread.start()
    try:
        server.serve_forever(poll_interval=.2)
    finally:
        run.stop.set()
        thread.join(timeout=90)
        server.server_close()
        device.close()


if __name__ == '__main__':
    main()
