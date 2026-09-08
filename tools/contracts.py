"""P1 host reference: explicit config bytes and small native CSV fixtures.

No device I/O. This deliberately bounded reference is not the P2 large-file viewer.
"""
import csv
from datetime import datetime, timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / 'schemas/config-v1.json').read_text(encoding='utf8'))['fields']
TYPES = {'u32': (1, '<I'), 'i32': (2, '<i'), 'f64': (3, '<d'),
         'bool': (4, '<?'), 'utf8': (5, None)}
HEADER = struct.Struct('<4sHHHHQIII')
COLUMNS = 'timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd,seq,t_us,vshunt_raw,vbus_raw,temp_raw,quality,Ah_net,Ahc,Ahd'.split(',')
MAGIC = b'# R1S3_LOG schema=1\n'
INVALID, GAP, SATURATED, UTC_UNKNOWN, TOTALS_INCOMPLETE = 1, 2, 4, 8, 16


class Unsupported(ValueError):
    pass


def crc(data):
    return zlib.crc32(data)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf8')


def strict_json(data):
    def pairs(items):
        result = {}
        for key, val in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = val
        return result
    def reject(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=reject)


def defaults():
    return {f['name']: f['default'] for f in REGISTRY}


def validate_config(values):
    if set(values) != {f['name'] for f in REGISTRY}:
        raise ValueError('Missing or unknown configuration fields')
    for f in REGISTRY:
        v, kind = values[f['name']], f['type']
        if kind == 'utf8':
            good = isinstance(v, str) and '\0' not in v and len(v.encode('utf8')) <= f['max_bytes']
        elif kind == 'bool':
            good = type(v) is bool
        else:
            good = (type(v) in (int, float) if kind == 'f64' else type(v) is int)
            good = good and math.isfinite(v) and f.get('min', -math.inf) <= v <= f.get('max', math.inf)
            good = good and ('enum' not in f or v in f['enum'])
        if not good:
            raise ValueError('Invalid field: ' + f['name'])
    date = values['calibration_utc']
    if date:
        parsed = datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
        if parsed.strftime('%Y-%m-%dT%H:%M:%SZ') != date:
            raise ValueError('Noncanonical calibration UTC')
    if values['calibration_valid'] and not all(values[k] for k in ('calibration_id', 'calibration_note', 'calibration_utc')):
        raise ValueError('Calibration provenance missing')


def encode_payload(values):
    validate_config(values)
    out = bytearray()
    for f in REGISTRY:
        code, fmt = TYPES[f['type']]
        value = values[f['name']]
        raw = struct.pack(fmt, value) if fmt else value.encode('utf8')
        out.extend(struct.pack('<HBBHH', f['id'], code, 0, len(raw), 0))
        out.extend(raw)
    if len(out) > 1472:
        raise ValueError('Payload exceeds slot')
    return bytes(out)


def decode_payload(data):
    pos, values = 0, {}
    for f in REGISTRY:
        if len(data) - pos < 8:
            raise ValueError('Truncated TLV')
        ident, code, r1, size, r2 = struct.unpack_from('<HBBHH', data, pos)
        expected, fmt = TYPES[f['type']]
        if (ident, code, r1, r2) != (f['id'], expected, 0, 0):
            raise ValueError('TLV ID/type/order/reserved mismatch')
        pos += 8
        raw = data[pos:pos+size]
        if len(raw) != size or (fmt and size != struct.calcsize(fmt)):
            raise ValueError('TLV length mismatch')
        if f['type'] == 'bool' and raw not in (b'\0', b'\1'):
            raise ValueError('Invalid bool byte')
        values[f['name']] = struct.unpack(fmt, raw)[0] if fmt else raw.decode('utf8')
        pos += size
    if pos != len(data):
        raise ValueError('Extra payload fields/bytes')
    validate_config(values)
    return values


def config_minor(values):
    return 0 if values['requested_rate_hz'] in (10, 50, 100) and values['max_gap_us'] <= 1000000 else 1


def encode_slot(values, generation):
    if type(generation) is not int or not 1 <= generation < 2**64:
        raise ValueError('Generation out of range; never wrap')
    payload = encode_payload(values)
    minor = config_minor(values)
    header = HEADER.pack(b'R1CF', 1, minor, 32, 0, generation, len(payload), 0, 0)
    checksum = crc(header + payload)
    header = header[:24] + struct.pack('<I', checksum) + header[28:]
    footer = struct.pack('<4sQII12s', b'RCMT', generation, checksum, len(payload), bytes(12))
    return header + payload + b'\xff' * (1472-len(payload)) + footer


def decode_slot(data):
    if len(data) != 1536:
        raise ValueError('Wrong slot size')
    magic, major, minor, hlen, r1, gen, size, checksum, r2 = HEADER.unpack(data[:32])
    if (magic, hlen, r1, r2) != (b'R1CF', 32, 0, 0) or not gen or size > 1472:
        raise ValueError('Invalid slot header')
    if data[1504:] != struct.pack('<4sQII12s', b'RCMT', gen, checksum, size, bytes(12)):
        raise ValueError('Uncommitted/torn footer')
    header = data[:24] + bytes(4) + data[28:32]
    payload = data[32:32+size]
    if crc(header + payload) != checksum:
        raise ValueError('Slot CRC mismatch')
    if major != 1 or minor not in (0, 1):
        raise Unsupported('Unsupported config version; inhibit writes')
    values = decode_payload(payload)
    if minor < config_minor(values):
        raise ValueError('Extended values require config minor 1')
    return gen, values


def select_slot(a, b):
    valid = []
    for label, raw in [('A', a), ('B', b)]:
        try:
            gen, values = decode_slot(raw)
            valid.append((gen, label, values))
        except Unsupported:
            raise
        except ValueError:
            pass
    if not valid:
        raise ValueError('No valid slot; expose defaults without saving')
    if len(valid) == 2 and valid[0][0] == valid[1][0] and valid[0][2] != valid[1][2]:
        raise ValueError('Ambiguous equal generation')
    return sorted(valid, key=lambda item: (-item[0], item[1]))[0]


def engineering(vshunt, vbus, temp, config):
    scale = 0.3125 if config['adc_range'] == 0 else 0.078125
    current = config['polarity'] * (vshunt * scale - config['i_zero_uV']) / config['shunt_uohm'] * config['i_gain']
    voltage = (vbus * .0001953125 - config['u_zero_V']) * config['u_gain']
    return current, voltage, current * voltage, temp * .0078125


def split_integral(a, b, dt_seconds):
    """Positive and absolute negative trapezoid areas, divided by 3600."""
    if a * b < 0:
        crossing = abs(a) / (abs(a) + abs(b))
        left = split_integral(a, 0, dt_seconds * crossing)
        right = split_integral(0, b, dt_seconds * (1-crossing))
        return left[0] + right[0], left[1] + right[1]
    area = (a+b) * .5 * dt_seconds / 3600
    return max(area, 0), max(-area, 0)


def validate_meta(meta):
    required = {'schema', 'session_id', 'part', 'previous_part_sha256', 'writer', 'hardware',
                'config', 'config_generation', 'config_sha256', 'acquisition', 'time',
                'raw', 'units', 'integration', 'description'}
    if set(meta) != required or meta['schema'] != 1:
        raise ValueError('Metadata keys/schema mismatch')
    if not isinstance(meta['session_id'], str) or not meta['session_id'] or not isinstance(meta['description'], str):
        raise ValueError('Missing session identity/description')
    if type(meta['part']) is not int or meta['part'] < 0 or type(meta['config_generation']) is not int or not 1 <= meta['config_generation'] < 2**64:
        raise ValueError('Invalid part/generation')
    prior = meta['previous_part_sha256']
    if (meta['part'] == 0 and prior is not None) or (meta['part'] > 0 and (not isinstance(prior, str) or len(prior) != 64 or any(ch not in '0123456789abcdef' for ch in prior))):
        raise ValueError('Missing/invalid part linkage')
    for key, keys in [('writer', {'name','version','commit','dirty'}),
                      ('hardware', {'board','sensor','sensor_address','manufacturer_id','device_id','topology','shunt_nameplate'}),
                      ('acquisition', {'requested_hz','measured_hz','adc_config','timestamp_note'})]:
        if not isinstance(meta[key], dict) or set(meta[key]) != keys:
            raise ValueError('Missing metadata interpretation: ' + key)
    if any(not isinstance(meta['writer'][k], str) or not meta['writer'][k] for k in ('name','version','commit')) or type(meta['writer']['dirty']) is not bool:
        raise ValueError('Invalid writer identity')
    hw = meta['hardware']
    if hw['sensor'] != 'INA228' or hw['topology'] not in ('low-side','high-side'):
        raise Unsupported('Unknown sensor/topology')
    for key in ('board','shunt_nameplate'):
        if not isinstance(hw[key], str) or not hw[key]: raise ValueError('Missing hardware description')
    for key, limit in [('sensor_address',127),('manufacturer_id',65535),('device_id',65535)]:
        if type(hw[key]) is not int or not 0 <= hw[key] <= limit: raise ValueError('Invalid hardware ID')
    validate_config(meta['config'])
    if meta['config_sha256'] != hashlib.sha256(encode_payload(meta['config'])).hexdigest():
        raise ValueError('Config snapshot hash mismatch')
    acq = meta['acquisition']
    if acq['requested_hz'] != meta['config']['requested_rate_hz'] or type(acq['adc_config']) is not int or not 0 <= acq['adc_config'] <= 65535:
        raise ValueError('Invalid acquisition snapshot')
    if acq['measured_hz'] is not None and (type(acq['measured_hz']) not in (int,float) or not math.isfinite(acq['measured_hz']) or acq['measured_hz'] <= 0):
        raise ValueError('Invalid measured cadence')
    if not isinstance(acq['timestamp_note'], str) or not acq['timestamp_note']:
        raise ValueError('Missing acquisition timing description')
    if meta['raw'] != {'vshunt': 'signed20', 'vbus': 'unsigned20', 'temp': 'signed16',
                        'vshunt_uV_lsb': .3125 if meta['config']['adc_range'] == 0 else .078125,
                        'vbus_V_lsb': .0001953125, 'temp_C_lsb': .0078125}:
        raise ValueError('Unsupported raw encoding/scales')
    if meta['integration'] != 'trapezoid-sign-split-no-gap-v1':
        raise Unsupported('Unknown integration policy')
    if meta['units'] != dict(I_A='A', U_V='V', P_W='W', Wh_net='Wh', Whc='Wh', Whd='Wh', Ah_net='Ah', Ahc='Ah', Ahd='Ah', t_us='us', ms_from_start='ms'):
        raise ValueError('Units mismatch')
    if set(meta['time']) != {'utc_anchor', 'anchor_t_us', 'uncertainty_us', 'source', 'sample_point'}:
        raise ValueError('Missing clock interpretation')
    if meta['time']['sample_point'] != 'conversion-ready-observed':
        raise Unsupported('Unknown sample time convention')
    clock = meta['time']
    if type(clock['anchor_t_us']) is not int or not 0 <= clock['anchor_t_us'] < 2**64:
        raise ValueError('Invalid clock anchor')
    if clock['utc_anchor'] is None:
        if clock['uncertainty_us'] is not None or clock['source'] != 'unknown' or not meta['config']['allow_unknown_utc']:
            raise ValueError('Unknown UTC policy mismatch')
    else:
        parse_utc(clock['utc_anchor'])
        if type(clock['uncertainty_us']) is not int or clock['uncertainty_us'] < 0 or not isinstance(clock['source'], str) or not clock['source'] or clock['source'] == 'unknown':
            raise ValueError('UTC source/uncertainty missing')


def parse_utc(value):
    result = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
    if result.strftime('%Y-%m-%dT%H:%M:%S.%fZ') != value:
        raise ValueError('UTC requires six fractional digits')
    return result


def encode_csv_row(row):
    stream = io.StringIO(newline='')
    csv.writer(stream, lineterminator='\n').writerow(['' if row[k] is None else row[k] for k in COLUMNS])
    return stream.getvalue().encode('utf8')


def write_native(meta, rows, block_rows=256, clean=True):
    validate_meta(meta)
    if not 1 <= block_rows <= 1024:
        raise ValueError('Invalid checkpoint interval')
    metaraw = b'# META ' + canonical(meta) + b'\n'
    out = bytearray(MAGIC + metaraw + f'# META_CRC32 {crc(metaraw):08X}\n'.encode() + (','.join(COLUMNS)+'\n').encode())
    for start in range(0, len(rows), block_rows):
        block = rows[start:start+block_rows]
        first = len(out)
        payload = b''.join(encode_csv_row(row) for row in block)
        out.extend(payload)
        checkpoint = dict(start=first, end=len(out), rows=len(block), first_seq=block[0]['seq'],
                          last_seq=block[-1]['seq'], crc32=f'{crc(payload):08X}')
        out.extend(b'# CHECKPOINT ' + canonical(checkpoint) + b'\n')
    if clean:
        end = dict(rows=len(rows), sha256=hashlib.sha256(out).hexdigest(), clean=True, reason='stop')
        out.extend(b'# END ' + canonical(end) + b'\n')
    # The reference writer must obey the same semantic contract as its decoder.
    read_native(bytes(out))
    return bytes(out)


def parse_row(raw, meta, previous):
    fields = next(csv.reader([raw.decode('utf8').rstrip('\n')], strict=True))
    if len(fields) != len(COLUMNS):
        raise ValueError('Wrong column count')
    row = dict(zip(COLUMNS, fields))
    for key in COLUMNS[1:]:
        value = row[key]
        if value == '':
            row[key] = None
        elif key in ('seq', 't_us', 'ms_from_start', 'vshunt_raw', 'vbus_raw', 'temp_raw', 'quality'):
            if value.strip() != value or not value.lstrip('-').isdigit():
                raise ValueError('Invalid integer')
            row[key] = int(value)
        else:
            row[key] = float(value)
            if not math.isfinite(row[key]):
                raise ValueError('Nonfinite sample')
    for key in ('seq', 't_us', 'ms_from_start', 'quality'):
        if type(row[key]) is not int or not 0 <= row[key] < 2**64:
            raise ValueError('Missing/out-of-range sample identity')
    q = row['quality']
    if q & ~31 or (q & SATURATED and not q & INVALID):
        raise ValueError('Unknown/inconsistent quality')
    if row['ms_from_start'] != row['t_us']//1000:
        raise ValueError('Conflicting monotonic times')
    if previous and (row['seq'] <= previous['seq'] or row['t_us'] <= previous['t_us']):
        raise ValueError('Nonmonotonic sample identity')
    if previous:
        gap = row['seq'] != previous['seq']+1 or row['t_us']-previous['t_us'] > meta['config']['max_gap_us']
        if gap and q & (GAP | TOTALS_INCOMPLETE) != GAP | TOTALS_INCOMPLETE:
            raise ValueError('Unmarked gap')
        if previous['quality'] & TOTALS_INCOMPLETE and not q & TOTALS_INCOMPLETE:
            raise ValueError('Lost incomplete-totals flag')
    if q & (INVALID | GAP) and not q & TOTALS_INCOMPLETE:
        raise ValueError('Incomplete totals must be explicit')
    for key, lo, hi in [('vshunt_raw', -524288, 524287), ('vbus_raw', 0, 1048575), ('temp_raw', -32768, 32767)]:
        val = row[key]
        if val is not None and not lo <= val <= hi:
            raise ValueError('Raw value out of range')
        if val is None and not q & INVALID:
            raise ValueError('Valid sample missing raw value')
        if val is not None and (val == hi or (lo < 0 and val == lo)) and not q & SATURATED:
            raise ValueError('Unmarked ADC rail')
    for key in ('I_A', 'U_V', 'P_W'):
        if (row[key] is None) != bool(q & INVALID):
            raise ValueError('Invalid sample must have empty engineering values')
    if not q & INVALID:
        expected = engineering(row['vshunt_raw'], row['vbus_raw'], row['temp_raw'], meta['config'])
        for key, val in zip(('I_A', 'U_V', 'P_W'), expected):
            if not math.isclose(row[key], val, rel_tol=1e-8, abs_tol=1e-9):
                raise ValueError('Raw/calibrated mismatch')
    for key in ('Wh_net', 'Whc', 'Whd', 'Ah_net', 'Ahc', 'Ahd'):
        if row[key] is None or (key not in ('Wh_net', 'Ah_net') and row[key] < 0):
            raise ValueError('Missing/negative totals')
    for net, plus, minus in [('Wh_net', 'Whc', 'Whd'), ('Ah_net', 'Ahc', 'Ahd')]:
        if not math.isclose(row[net], row[plus]-row[minus], rel_tol=1e-8, abs_tol=1e-9):
            raise ValueError('Net total mismatch')
    for source, plus, minus in [('P_W','Whc','Whd'), ('I_A','Ahc','Ahd')]:
        if previous:
            expected_plus, expected_minus = previous[plus], previous[minus]
            if not (q | previous['quality']) & INVALID and not q & GAP:
                inc_plus, inc_minus = split_integral(previous[source], row[source], (row['t_us']-previous['t_us'])/1e6)
                expected_plus += inc_plus
                expected_minus += inc_minus
        elif meta['part'] == 0:
            expected_plus = expected_minus = 0
        else:
            continue  # Prior part linkage is a separate multi-file validation step.
        if not all(math.isclose(row[key], val, rel_tol=1e-8, abs_tol=1e-9) for key,val in [(plus,expected_plus),(minus,expected_minus)]):
            raise ValueError('Integration total mismatch')
    unknown = meta['time']['utc_anchor'] is None
    if bool(q & UTC_UNKNOWN) != unknown or (not row['timestamp']) != unknown:
        raise ValueError('UTC validity mismatch')
    if not unknown:
        expected_time = parse_utc(meta['time']['utc_anchor']) + timedelta(microseconds=row['t_us']-meta['time']['anchor_t_us'])
        if parse_utc(row['timestamp']) != expected_time:
            raise ValueError('UTC anchor/sample mismatch')
    return row


def read_native(data):
    if len(data) > 16*1024*1024:
        raise ValueError('Reference decoder limit: 16 MiB; production streaming is P2')
    if not data.startswith(MAGIC):
        raise Unsupported('Unsupported native magic/version')
    if b'\r' in data or data.startswith(b'\xef\xbb\xbf'):
        raise ValueError('Native requires UTF8 without BOM and LF')
    lines = data.splitlines(keepends=True)
    if len(lines) < 4 or not lines[1].startswith(b'# META ') or len(lines[1]) > 16384:
        raise ValueError('Missing/oversized metadata')
    meta = strict_json(lines[1][7:])
    validate_meta(meta)
    if lines[2] != f'# META_CRC32 {crc(lines[1]):08X}\n'.encode():
        raise ValueError('Metadata CRC mismatch')
    if lines[3] != (','.join(COLUMNS)+'\n').encode():
        raise ValueError('Native columns mismatch')
    offset = sum(map(len, lines[:4]))
    start, pending, verified, previous = offset, [], [], None
    clean = False
    for index, raw in enumerate(lines[4:], 4):
        if not raw.endswith(b'\n'):
            break  # Partial final line is explicitly unverified.
        if raw.startswith(b'# CHECKPOINT '):
            if len(raw) > 1024:
                raise ValueError('Oversized checkpoint')
            cp = strict_json(raw[13:])
            if not pending:
                raise ValueError('Empty checkpoint')
            expected = dict(start=start, end=offset, rows=len(pending), first_seq=pending[0]['seq'], last_seq=pending[-1]['seq'], crc32=f'{crc(data[start:offset]):08X}')
            if cp != expected:
                raise ValueError('Checkpoint bounds/count/CRC mismatch')
            verified.extend(pending)
            pending = []
            start = offset + len(raw)
        elif raw.startswith(b'# END '):
            if len(raw) > 1024:
                raise ValueError('Oversized end record')
            end = strict_json(raw[6:])
            if pending or index != len(lines)-1 or set(end) != {'rows', 'sha256', 'clean', 'reason'}:
                raise ValueError('Invalid finalization')
            if end['rows'] != len(verified) or end['sha256'] != hashlib.sha256(data[:offset]).hexdigest() or end['clean'] is not True or end['reason'] not in ('stop', 'rotation'):
                raise ValueError('END count/digest/status mismatch')
            clean = True
        else:
            if raw.startswith(b'#') or len(raw) > 4096 or len(pending) >= 1024:
                raise ValueError('Unknown control/oversized block')
            previous = parse_row(raw, meta, previous)
            pending.append(previous)
        offset += len(raw)
    return dict(metadata=meta, rows=verified, unverified_rows=pending, clean=clean,
                partial_line=bool(lines and not lines[-1].endswith(b'\n')))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    result = read_native(args.file.read_bytes())
    print(json.dumps(dict(verified_rows=len(result['rows']), unverified_rows=len(result['unverified_rows']), clean=result['clean'], partial_line=result['partial_line']), indent=2))
