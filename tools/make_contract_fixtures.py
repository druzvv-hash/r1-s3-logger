"""Deterministic synthetic public fixtures; never reads owner recordings."""
import hashlib
import json
from pathlib import Path
from contracts import defaults, encode_payload, encode_slot, engineering, split_integral, write_native, COLUMNS

OUT = Path(__file__).resolve().parents[1] / 'tests/fixtures'


def metadata():
    config = defaults()
    config['allow_unknown_utc'] = True
    return dict(schema=1, session_id='synthetic-contract-001', part=0, previous_part_sha256=None,
                writer=dict(name='P1-reference', version='1.0', commit='synthetic', dirty=False),
                hardware=dict(board='ESP32-S3-N32R16V', sensor='INA228', sensor_address=64,
                              manufacturer_id=21577, device_id=8833, topology='low-side', shunt_nameplate='60mV/400A'),
                config=config, config_generation=1, config_sha256=hashlib.sha256(encode_payload(config)).hexdigest(),
                acquisition=dict(requested_hz=50, measured_hz=None, adc_config=31592,
                                 timestamp_note='synthetic; sequential channels, ready-observation time'),
                time=dict(utc_anchor=None, anchor_t_us=0, uncertainty_us=None, source='unknown', sample_point='conversion-ready-observed'),
                raw=dict(vshunt='signed20', vbus='unsigned20', temp='signed16', vshunt_uV_lsb=.3125, vbus_V_lsb=.0001953125, temp_C_lsb=.0078125),
                units=dict(I_A='A', U_V='V', P_W='W', Wh_net='Wh', Whc='Wh', Whd='Wh', Ah_net='Ah', Ahc='Ah', Ahd='Ah', t_us='us', ms_from_start='ms'),
                integration='trapezoid-sign-split-no-gap-v1', description='Synthetic public fixture, no bench data')


def samples(meta, specs):
    rows = []
    wc = wd = ac = ad = 0.0
    incomplete = False
    for seq, tus, raw_i in specs:
        q = 8
        if rows and (seq != rows[-1]['seq']+1 or tus-rows[-1]['t_us'] > meta['config']['max_gap_us']):
            q |= 2
            incomplete = True
        if raw_i is None:
            q |= 1
            incomplete = True
            i = u = p = None
            raw_u = raw_t = None
        else:
            raw_u, raw_t = 25600, 3200  # exactly 5 V and 25 C
            i, u, p, _ = engineering(raw_i, raw_u, raw_t, meta['config'])
        if incomplete:
            q |= 16
        if rows and not ((q | rows[-1]['quality']) & 1) and not q & 2:
            dt = (tus - rows[-1]['t_us'])/1e6
            a, b = split_integral(rows[-1]['P_W'], p, dt)
            wc += a; wd += b
            a, b = split_integral(rows[-1]['I_A'], i, dt)
            ac += a; ad += b
        row = dict(timestamp='', ms_from_start=tus//1000, I_A=i, U_V=u, P_W=p,
                   Wh_net=wc-wd, Whc=wc, Whd=wd, seq=seq, t_us=tus,
                   vshunt_raw=raw_i, vbus_raw=raw_u, temp_raw=raw_t, quality=q,
                   Ah_net=ac-ad, Ahc=ac, Ahd=ad)
        rows.append(row)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = metadata()
    rows = samples(meta, [(0,0,480), (1,20000,480), (2,40000,-480), (3,60000,-480)])
    native = write_native(meta, rows, block_rows=2)
    gap = samples(meta, [(0,0,480), (1,20000,None), (4,80000,-480), (5,100000,-480)])
    files = {
        'native-sign-crossing.csv': native,
        'native-gap.csv': write_native(meta, gap, block_rows=2),
        'native-interrupted.csv': native[:native.index(b'# END ')],
        'native-truncated.csv': native[:native.index(b'# CHECKPOINT ', native.index(b'# CHECKPOINT ')+1)-10],
        'native-bad-crc.csv': native.replace(b',480,25600,', b',481,25600,', 1),
        'native-unknown.csv': native.replace(b'schema=1\n', b'schema=2\n', 1),
        'config-default-slot.hex': (encode_slot(defaults(), 1).hex()+'\n').encode(),
        'config-default.json': (json.dumps(dict(schema='r1s3-config', major=1, minor=0, values=defaults()), indent=2)+'\n').encode(),
        'r1-eight.csv': b'timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd\n# rate_hz=50\n2025-12-21 12:00:00,0,1,5,5,0,0,0\n2025-12-21 12:00:00,20,-1,5,-5,0,0.000006944444,0.000006944444\n',
        'r1-pss.csv': b'timestamp,ms_from_start,I_A,U_V,P_W,Pss_Wh\n2025-01-01 00:00:00,0,1,5,5,0\n',
        'r1-short.csv': b'timestamp,ms,I,U,P,Wh\n2025-01-01 00:00:00,0,1,5,5,0\n',
        'r1-short-eight.csv': b'timestamp,ms,I,U,P,Wh,Whc,Whd\n2025-01-01 00:00:00,0,1,5,5,0,0,0\n',
        'r1-bom-crlf.csv': b'\xef\xbb\xbf# rate_hz=50\r\ntimestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd\r\n2025-01-01 00:00:00,0,1,5,5,0,0,0\r\n',
        'r1-invalid.csv': b'timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd\n2025-01-01 00:00:00,0,NaN,,5,0,0,0\n',
        'r1-headerless.csv': b'2025-01-01 00:00:00,0,1,5,5,0\n',
    }
    expectations = {
        'native-sign-crossing.csv': dict(verified_rows=4, clean=True, last_I_A=-1, last_U_V=5, Whc=0.00003472222222222222, Whd=0.00003472222222222222),
        'native-gap.csv': dict(verified_rows=4, clean=True, invalid_rows=1, last_quality=24, Whc=0, Whd=0.00002777777777777778),
        'native-interrupted.csv': dict(verified_rows=4, clean=False),
        'native-truncated.csv': dict(verified_rows=2, clean=False, unverified_rows=1, partial_line=True),
        'native-bad-crc.csv': dict(error='corrupt'), 'native-unknown.csv': dict(error='unsupported'),
        'r1-eight.csv': dict(adapter='r1-eight', rows=2, utc='unknown timezone', comments_are_rows=False),
        'r1-pss.csv': dict(adapter='r1-pss', energy='preserve Pss_Wh, meaning unresolved'),
        'r1-short.csv': dict(adapter='needs-confirmed-mapping'),
        'r1-short-eight.csv': dict(adapter='needs-confirmed-mapping'),
        'r1-bom-crlf.csv': dict(adapter='r1-eight', rows=1),
        'r1-invalid.csv': dict(adapter='r1-eight', invalid_rows=1, substitute_zero=False),
        'r1-headerless.csv': dict(adapter='needs-confirmed-mapping'),
    }
    manifest = dict(origin='All payloads synthetic; legacy header layouts only are copied from inventory.',
                    fixtures={})
    for name, raw in files.items():
        (OUT/name).write_bytes(raw)
        manifest['fixtures'][name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), expected=expectations.get(name, {'config_generation':1}))
    (OUT/'manifest.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf8'))


if __name__ == '__main__':
    main()
