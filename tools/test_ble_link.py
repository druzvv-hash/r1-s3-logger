"""Opt-in R3/R1 BLE bench acceptance through the existing USB panel.

Flashes nothing. Requires idle R1 with its panel bridge running and R3 on the
explicit serial port. Exercises pairing, rejection, reconnect and SD recording.
PIN stays in memory. Evidence/files go to ignored data/ble-acceptance/<label>.
Restores exact runtime settings without SAVE; leaves the selected BLE link on.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

import serial
import contracts
from analyze_rate_record import analyze

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hardware', action='store_true', required=True)
    parser.add_argument('--r3-port', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--seconds', type=int, default=20)
    args = parser.parse_args()
    if not args.label.replace('-', '').replace('_', '').isalnum() or not 10 <= args.seconds <= 120:
        parser.error('Simple label and duration 10..120 seconds required')
    out = ROOT/'data/ble-acceptance'/args.label
    out.mkdir(parents=True, exist_ok=False)
    session = json.loads((ROOT/'data/device-panel/session.json').read_text())['url']
    base, token = session.split('?', 1)

    def url(route, extra=''):
        return base.rstrip('/')+route+'?'+token+extra

    def api(route, body=None):
        req = urllib.request.Request(url(route), data=None if body is None else body.encode(),
                                     headers={'X-R1-Panel': '1', 'Content-Type': 'text/plain'})
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)

    initial = api('/api/state')
    assert initial['recording_state'] == 'READY' and not initial['file_transfer'] and 'ble' in initial
    (out/'baseline-private.json').write_text(json.dumps(initial))
    samples, records = [], []
    owned = ''
    source_disabled = False

    def state():
        s = api('/api/state')
        assert s['boot'] == initial['boot'], 'Unexpected R1 restart'
        samples.append({k: v for k, v in s.items() if k not in ('ap_password', 'ssid', 'config_hex')})
        return s

    def command(text):
        s = state()
        r = api('/api/command', f"{s['boot']} {s['revision']} {text}")
        assert r.get('ok'), r.get('message', 'Command rejected')

    def wait_for(predicate, timeout=25):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            s = state()
            if predicate(s):
                return s
            time.sleep(.4)
        raise TimeoutError('BLE acceptance condition did not complete')

    def r3(command_text):
        port = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=2)
        port.dtr = False; port.rts = False; port.port = args.r3_port
        port.open()
        try:
            port.reset_input_buffer(); port.write((command_text+'\n').encode())
            deadline = time.monotonic()+4
            while time.monotonic() < deadline:
                try:
                    obj = json.loads(port.readline())
                except (ValueError, UnicodeDecodeError):
                    continue
                if obj.get('type') in ('ble', 'ble_request'):
                    return obj
        finally:
            port.close()
        raise TimeoutError('R3 BLE console did not respond')

    def connect(pair):
        command('BLE CONNECT '+pair['device_id']+' '+pair['pairing_pin'])
        s = wait_for(lambda v: v['ble']['authenticated'] and v['ble']['fresh'])
        assert int(s['ble']['source_boot']) == int(pair['boot_id'], 16)
        assert s['ble']['mtu'] >= 67 and not s['ble']['synchronized']
        return s

    try:
        pair = r3('ble pair')
        assert pair['ready'] and pair['enabled']
        connected = connect(pair)
        print('PASS authenticated identity, MTU and fresh beacons', flush=True)
        wrong = str((int(pair['pairing_pin'])+1) % 1000000).zfill(6)
        command('BLE CONNECT '+pair['device_id']+' '+wrong)
        wait_for(lambda s: not s['ble']['authenticated'] and not s['ble']['fresh'])
        before = state()['ble']['received']
        end = time.monotonic()+6
        while time.monotonic() < end:
            s = state()
            assert not s['ble']['authenticated'] and not s['ble']['fresh'] and s['ble']['received'] == before
            time.sleep(.5)
        command('BLE OFF'); wait_for(lambda s: s['ble']['state'] == 'OFF')
        connected = connect(pair)
        print('PASS wrong PIN rejected; correct PIN reconnects', flush=True)
        config = contracts.decode_payload(bytes.fromhex(initial['config_hex']))
        js = "const fs=require('fs'),{configForRate}=require('./device_ui/rate_profile.js');const v=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify([50,150,300].map(hz=>configForRate(v,hz))));"
        profiles = json.loads(subprocess.check_output(['node', '-e', js], input=json.dumps(config).encode(), cwd=ROOT))
        for profile in profiles:
            hz = profile['requested_rate_hz']
            command('APPLY '+contracts.encode_payload(profile).hex())
            wait_for(lambda s: s['requested_hz'] == hz)
            before = state()
            command('START')
            s = wait_for(lambda s: s['recording_state'] == 'RUNNING')
            owned = s['recording_path']
            began = time.monotonic()
            if hz == 300:
                previous_segment = int(s['ble']['segment'])
                r3('ble off'); source_disabled = True
                wait_for(lambda s: not s['ble']['fresh'], timeout=8)
                time.sleep(2)
                r3('ble on'); source_disabled = False
                s = wait_for(lambda s: s['ble']['fresh'] and int(s['ble']['segment']) > previous_segment)
                print('PASS source off/on reconnect while recording at 300 Hz', flush=True)
            while time.monotonic()-began < args.seconds:
                s = state()
                assert s['recording_state'] == 'RUNNING' and s['recording_path'] == owned
                assert s['ble']['fresh'] and s['ble']['authenticated']
                time.sleep(.5)
            command('STOP')
            s = wait_for(lambda s: s['recording_state'] == 'READY')
            path = owned; owned = ''
            result = dict(hz=hz, path=path, rows=s['recording_rows'],
                          seconds=s['recording_seconds'], missed=s['missed_samples']-before['missed_samples'],
                          invalid=s['invalid_samples']-before['invalid_samples'], overflows=s['recording_overflows'],
                          beacons=int(s['ble']['received'])-int(before['ble']['received']))
            records.append(result)
            assert result['missed'] == result['invalid'] == result['overflows'] == 0, result
            assert result['beacons'] > 0 and s['generation'] == initial['generation']
            print('PASS recording '+json.dumps(result), flush=True)
        command('APPLY '+initial['config_hex'])
        restored = wait_for(lambda s: s['config_hex'] == initial['config_hex'])
        assert restored['generation'] == initial['generation']
        for record in records:
            dest = out/Path(record['path']).name
            with urllib.request.urlopen(url('/api/download', '&path='+record['path'].encode().hex()), timeout=30) as response, dest.open('wb') as target:
                expected = int(response.headers['Content-Length'])
                while chunk := response.read(65536):
                    target.write(chunk)
            assert dest.stat().st_size == expected
            result = analyze(dest)
            assert result['clean'] and result['verified_rows'] == record['rows']
            assert not any(result[k] for k in ('missing_sequences','invalid_rows','gap_rows','unverified_rows','partial_line'))
            record['file'] = result
            print('PASS downloaded and verified '+json.dumps({k: result[k] for k in ('requested_hz','verified_rows','actual_hz','viewer_integrity')}), flush=True)
        source = r3('ble?')
        assert source['authenticated_clients'] == 1 and source['notify_errors'] == source['drops'] == 0
        (out/'source-final.json').write_text(json.dumps(source, indent=2))
        print('PASS BLE acceptance; original settings restored without SAVE', flush=True)
    finally:
        (out/'snapshots.json').write_text(json.dumps(samples))
        (out/'recordings.json').write_text(json.dumps(records, indent=2))
        if source_disabled:
            r3('ble on')
        s = api('/api/state')
        if s['boot'] == initial['boot']:
            if owned and s['recording_path'] == owned and s['recording_state'] == 'RUNNING':
                command('STOP'); s = wait_for(lambda s: s['recording_state'] == 'READY')
            if s['recording_state'] == 'READY' and s['config_hex'] != initial['config_hex']:
                command('APPLY '+initial['config_hex'])
                wait_for(lambda s: s['config_hex'] == initial['config_hex'])


if __name__ == '__main__':
    main()
