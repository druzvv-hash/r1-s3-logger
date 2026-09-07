"""Offline viewer adapters and disk-backed full-resolution analysis.

Source recordings are read only. Native semantics reuse the P1 contract oracle.
"""
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import contracts as c

MAX_FILE = 1024**3
MAX_ROWS = 10_000_000
UNITS = dict(I_A='A', U_V='V', P_W='W', Wh_net='Wh', Whc='Wh', Whd='Wh',
             Ah_net='Ah', Ahc='Ah', Ahd='Ah', Pss_Wh='Wh (meaning unverified)')
R1 = c.COLUMNS[:8]
SHORT = ['timestamp','ms','I','U','P','Wh']


class MappingRequired(ValueError):
    def __init__(self, message, preview):
        super().__init__(message)
        self.preview = preview


class Lines:
    def __init__(self, source):
        self.source, self.offset, self.number = source, 0, 0

    def read(self, limit=65536):
        raw = self.source.readline(limit+1)
        if len(raw) > limit:
            raise ValueError(f'Line {self.number+1} exceeds {limit} bytes')
        self.offset += len(raw)
        self.number += bool(raw)
        if self.offset > MAX_FILE:
            raise ValueError('File exceeds 1 GiB viewer limit')
        return raw


class Session:
    def __init__(self, database):
        self.db = sqlite3.connect(database, check_same_thread=False)
        self.db.execute('PRAGMA cache_size=-4096')
        self.db.execute('PRAGMA temp_store=FILE')
        self.db.execute('CREATE TABLE samples(n INTEGER PRIMARY KEY, segment INTEGER, seconds REAL, payload TEXT)')
        self.summary = dict(format='', rows=0, invalid_rows=0, comments=0, skipped_rows=0,
                            unverified_rows=0, partial_line=False, integrity='', metadata={},
                            channels={}, segments=[], diagnostics=[], diagnostic_count=0)
        self.segment = -1
        self.base_us = 0
        self.last_us = None
        self.pending_break = False

    def diagnostic(self, message, line=None):
        self.summary['diagnostic_count'] += 1
        if len(self.summary['diagnostics']) < 200:
            self.summary['diagnostics'].append(dict(line=line, message=message))

    def add(self, row, line, byte, *, force_segment=False):
        tus = row['t_us']
        if self.summary['rows'] >= MAX_ROWS:
            raise ValueError('File exceeds 10 million sample limit')
        if self.last_us is None or force_segment or tus <= self.last_us:
            if self.segment >= 999:
                raise ValueError('More than 1000 time segments; split this recording before import')
            if self.last_us is not None:
                self.diagnostic('Time reset/repeated timestamp: new segment; never joined', line)
            self.segment += 1
            self.base_us = tus
            self.summary['segments'].append(dict(id=self.segment, rows=0, start_us=str(tus), duration_s=0))
        seconds = (tus-self.base_us)/1e6
        row = dict(row, t_us=str(tus), segment=self.segment, line=line, byte=byte,
                   break_before=bool(self.pending_break or row.get('quality',0) & c.GAP))
        if 'seq' in row: row['seq'] = str(row['seq'])
        self.pending_break = False
        self.summary['rows'] += 1
        if row.get('quality',0) & c.INVALID:
            self.summary['invalid_rows'] += 1
        seg = self.summary['segments'][-1]
        seg['rows'] += 1
        seg['duration_s'] = seconds
        self.last_us = tus
        self.db.execute('INSERT INTO samples VALUES(?,?,?,?)',
                        (self.summary['rows'],self.segment,seconds,json.dumps(row,allow_nan=False)))
        if self.summary['rows'] % 4096 == 0: self.db.commit()

    def finish(self):
        self.db.execute('CREATE INDEX time_index ON samples(segment,seconds)')
        self.db.commit()
        return self

    def close(self):
        self.db.close()

    def window(self, segment, start, end, channels, pixels=1000):
        if not 0 <= segment < len(self.summary['segments']):
            raise ValueError('Unknown segment')
        if not all(math.isfinite(v) for v in (start,end)) or start < 0 or end < start:
            raise ValueError('Invalid time range')
        if not 1 <= len(channels) <= 8 or len(set(channels)) != len(channels) or any(k not in self.summary['channels'] for k in channels):
            raise ValueError('Unknown channel')
        pixels = max(50,min(int(pixels),2000))
        base = int(self.summary['segments'][segment]['start_us'])
        low = int(Decimal(str(start))*1_000_000)+base
        high = int(Decimal(str(end))*1_000_000)+base
        stats = {k:dict(count=0,min=None,max=None,sum=0.0,first=None,last=None,positive=0.0,negative=0.0,covered_s=0.0) for k in channels}
        # Fixed pixel bins: preserve extrema and discontinuities without allocating per input row.
        bins = {k:{} for k in channels}
        previous = None
        rows = 0
        for seconds,payload in self.db.execute('SELECT seconds,payload FROM samples WHERE segment=? AND seconds>=? AND seconds<=? ORDER BY n',(segment,start-1e-9,end+1e-9)):
            row = json.loads(payload)
            tus = int(row['t_us'])
            if not low <= tus <= high: continue
            rows += 1
            bucket = min(pixels-1,max(0,int((seconds-start)/max(end-start,1e-12)*pixels)))
            for key in channels:
                val = row.get(key)
                valid = val is not None and not (row['quality'] & c.INVALID)
                cell = bins[key].setdefault(bucket,dict(x0=seconds,x1=seconds,min=None,max=None,broken=False))
                cell['x1'] = seconds
                cell['broken'] |= bool(not valid or row['break_before'])
                if not valid: continue
                cell['min'] = val if cell['min'] is None else min(cell['min'],val)
                cell['max'] = val if cell['max'] is None else max(cell['max'],val)
                st = stats[key]
                st['count'] += 1; st['sum'] += val
                st['min'] = val if st['min'] is None else min(st['min'],val)
                st['max'] = val if st['max'] is None else max(st['max'],val)
                if st['first'] is None: st['first'] = val
                st['last'] = val
                if previous and previous.get(key) is not None and not previous['quality'] & c.INVALID and not row['break_before']:
                    dt = (tus-int(previous['t_us']))/1e6
                    if dt > 0:
                        st['covered_s'] += dt
                        if key in ('I_A','P_W'):
                            pos,neg = c.split_integral(previous[key],val,dt)
                            st['positive'] += pos; st['negative'] += neg
            previous = row
        for st in stats.values():
            st['mean'] = st.pop('sum')/st['count'] if st['count'] else None
            st['missing_s'] = max(0,end-start-st['covered_s'])
        return dict(rows=rows, start=start,end=end,stats=stats,
                    envelopes={k:list(v.values()) for k,v in bins.items()})


def native(lines, first, session):
    if first != c.MAGIC: raise c.Unsupported('Unsupported R1S3 version')
    digest = hashlib.sha256(first)
    rawmeta = lines.read(16384)
    if not rawmeta.startswith(b'# META ') or not rawmeta.endswith(b'\n') or b'\r' in rawmeta:
        raise ValueError('Missing/corrupt native metadata')
    meta = c.strict_json(rawmeta[7:]); c.validate_meta(meta)
    crcmeta = lines.read(1024)
    if crcmeta != f'# META_CRC32 {c.crc(rawmeta):08X}\n'.encode():
        raise ValueError('Metadata CRC mismatch')
    header = lines.read(4096)
    if header != (','.join(c.COLUMNS)+'\n').encode(): raise ValueError('Native columns mismatch')
    for raw in (rawmeta,crcmeta,header): digest.update(raw)
    session.summary.update(format='R1S3 CSV v1',metadata=meta,channels={k:v for k,v in UNITS.items() if k in c.COLUMNS},integrity='interrupted')
    start, block_crc, pending, previous = lines.offset,0,[],None
    ended = False
    while True:
        offset, number = lines.offset, lines.number+1
        raw = lines.read(4096)
        if not raw: break
        if ended: raise ValueError('Bytes after END')
        if b'\r' in raw: raise ValueError('Native requires LF, not CRLF')
        if not raw.endswith(b'\n'):
            session.summary['partial_line'] = True
            break
        if raw.startswith(b'# CHECKPOINT '):
            if len(raw)>1024 or not pending: raise ValueError('Invalid checkpoint size/block')
            cp = c.strict_json(raw[13:])
            expected = dict(start=start,end=offset,rows=len(pending),first_seq=pending[0][0]['seq'],last_seq=pending[-1][0]['seq'],crc32=f'{block_crc:08X}')
            if cp != expected: raise ValueError(f'Checkpoint count/bounds/CRC mismatch at line {number}')
            for row,ln,byte in pending: session.add(row,ln,byte)
            pending=[]; block_crc=0; start=lines.offset
        elif raw.startswith(b'# END '):
            if len(raw)>1024: raise ValueError('Oversized END')
            end = c.strict_json(raw[6:])
            if pending or set(end) != {'rows','sha256','clean','reason'} or end['rows'] != session.summary['rows'] or end['sha256'] != digest.hexdigest() or end['clean'] is not True or end['reason'] not in ('stop','rotation'):
                raise ValueError('END count/digest/status mismatch')
            ended=True; session.summary['integrity']='verified clean'
        else:
            if raw.startswith(b'#') or len(pending)>=1024: raise ValueError('Unknown control/oversized native block')
            previous = c.parse_row(raw,meta,previous)
            pending.append((previous,number,offset))
            block_crc=zlib.crc32(raw,block_crc)
        digest.update(raw)
    session.summary['unverified_rows']=len(pending)
    if not ended:
        session.diagnostic('Interrupted file: only checkpoint-verified rows enter plots/statistics; trailing rows excluded')
    if meta['part']>0: session.diagnostic('Rotation part opened independently; previous-part linkage has not been verified')


def numeric(value, decimal_comma=False):
    value=value.strip()
    if decimal_comma: value=value.replace(',','.')
    try: result=float(value)
    except ValueError: return None
    return result if math.isfinite(result) else None


def legacy(lines, first, session, options):
    delimiter=options.get('delimiter',',')
    if delimiter not in (',',';','\t'): raise ValueError('Unsupported delimiter')
    decimal_comma=options.get('decimal_comma',False)
    if decimal_comma and delimiter==',': raise ValueError('Decimal comma requires semicolon or tab delimiter')
    mapping=options.get('mapping','auto')
    allowed={'auto','short','headerless-six','headerless-eight'}
    if mapping not in allowed: raise ValueError('Unknown confirmed mapping')
    maxgap=options.get('max_gap_ms',1000)
    if type(maxgap) not in (int,float) or not math.isfinite(maxgap) or not 0<maxgap<=3600000:
        raise ValueError('Invalid maximum legacy gap')
    zone=options.get('utc_offset_min')
    if zone is not None and (type(zone) is not int or not -720<=zone<=840): raise ValueError('Invalid timezone offset')
    headers=None; columns=None; previous=None; inferred_gap=None; raw=first
    session.summary.update(format='R1 CSV',integrity='legacy — no checksum',metadata=dict(timezone_offset_min=zone,timezone='unverified local time' if zone is None else 'user supplied fixed offset',options=options))
    def parse_record(raw):
        # csv.reader requests continuation lines only for a quoted multiline field.
        def pieces():
            total=len(raw); yield raw.decode('utf-8-sig')
            while True:
                more=lines.read()
                if not more: return
                total+=len(more)
                if total>65536: raise ValueError('CSV record exceeds 64 KiB')
                yield more.decode('utf8')
        return next(csv.reader(pieces(),delimiter=delimiter,strict=True))
    while raw:
        number,byte=lines.number,lines.offset-len(raw)
        stripped=raw.decode('utf-8-sig').strip()
        if not stripped or stripped.startswith('#'):
            if stripped.startswith('#'):
                session.summary['comments']+=1
                # Matched R1 writer's nominal metadata is a gap heuristic, not measured cadence.
                import re
                match=re.search(r'interval_us\s*[=:]\s*(\d+)',stripped)
                if match and int(match[1])>0: inferred_gap=2*int(match[1])
            raw=lines.read(); continue
        try: fields=parse_record(raw)
        except csv.Error as exc:
            session.diagnostic('Malformed CSV quoting: '+str(exc),number)
            session.summary['skipped_rows']+=1; session.pending_break=True
            raw=lines.read(); continue
        if headers is None:
            if mapping.startswith('headerless'):
                headers=SHORT+(['Whc','Whd'] if mapping=='headerless-eight' else [])
            else:
                headers=[s.strip() for s in fields]
            if len(headers)>64: raise ValueError('Excessive columns')
            if len(headers)!=len(set(headers)):
                if 'timestamp' not in headers:
                    raise MappingRequired('No recognized header. Choose a confirmed headerless mapping.',fields[:16])
                raise ValueError('Duplicate columns')
            if set(R1).issubset(headers):
                columns={k:k for k in headers}; session.summary['format']='R1 eight-column CSV'
            elif set(R1[:5]+['Pss_Wh']).issubset(headers):
                columns={k:k for k in headers}; session.summary['format']='R1 Pss CSV'
                session.diagnostic('Pss_Wh preserved separately: accumulator meaning unresolved; not Wh_net')
            elif mapping!='auto' and set(SHORT).issubset(headers):
                aliases=dict(ms='ms_from_start',I='I_A',U='U_V',P='P_W',Wh='Wh_net')
                columns={k:aliases.get(k,k) for k in headers}
                if len(set(columns.values()))!=len(columns): raise ValueError('Ambiguous alias columns')
                session.summary['format']='R1 confirmed short mapping'
                session.diagnostic('User confirmed ms / A / V / W / net Wh mapping; source semantics not independently verified')
            else:
                raise MappingRequired('Header is ambiguous. Confirm units/mapping or delimiter before import.',fields[:16])
            # Keep unknown columns but isolate names from normalized model fields.
            columns={key:(val if val in UNITS or val in ('timestamp','ms_from_start') else 'extra:'+val) for key,val in columns.items()}
            session.summary['channels']={columns[k]:UNITS.get(columns[k],'unknown') for k in headers if columns[k] not in ('timestamp','ms_from_start')}
            session.summary['metadata']['source_columns']=headers
            if not mapping.startswith('headerless'):
                raw=lines.read(); continue
        if [f.strip() for f in fields]==headers:
            session.pending_break=True; previous=None; session.last_us=None
            session.diagnostic('Repeated header: next sample starts a new segment',number)
            raw=lines.read(); continue
        if 'timestamp' in [f.strip() for f in fields]:
            raise ValueError(f'Header layout changed at line {number}; split mixed-format sessions before import')
        if len(fields)!=len(headers):
            session.diagnostic('Wrong column count: row excluded; continuity broken',number)
            session.summary['skipped_rows']+=1; session.pending_break=True
            raw=lines.read(); continue
        values={columns[k]:v for k,v in zip(headers,fields)}
        try:
            timevalue=values['ms_from_start'].strip()
            if decimal_comma: timevalue=timevalue.replace(',','.')
            tus_decimal=Decimal(timevalue)*1000
            if not tus_decimal.is_finite() or tus_decimal<0 or tus_decimal>=2**64 or tus_decimal!=tus_decimal.to_integral_value():
                raise ValueError('Bad time')
            tus=int(tus_decimal)
        except (InvalidOperation,ValueError):
            session.diagnostic('Missing/invalid relative time: row excluded',number)
            session.summary['skipped_rows']+=1;session.pending_break=True
            raw=lines.read();continue
        row=dict(t_us=tus,timestamp=values['timestamp'],quality=0,utc=None)
        for key in session.summary['channels']:
            row[key]=numeric(values[key],decimal_comma)
        if any(row.get(k) is None for k in ('I_A','U_V','P_W')):
            row['quality']|=c.INVALID
            session.diagnostic('Invalid measurement: blanks/NaN/malformed values retained as null, never zero',number)
        if any(row[k] is None for k in session.summary['channels'] if k not in ('I_A','U_V','P_W')):
            session.diagnostic('Unavailable optional/extra column value retained as null',number)
        gap_us=int(inferred_gap if inferred_gap is not None else maxgap*1000)
        if previous is not None and tus>previous and tus-previous>gap_us:
            row['quality']|=c.GAP
            session.diagnostic('Time gap above legacy threshold; excluded from integration',number)
        previous=tus
        if zone is not None:
            try:
                stamp=datetime.fromisoformat(row['timestamp'])
                if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone(timedelta(minutes=zone)))
                row['utc']=stamp.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
            except ValueError: session.diagnostic('Legacy wall-clock text could not be interpreted; relative time retained',number)
        session.add(row,number,byte)
        raw=lines.read()
    if headers is None: raise ValueError('No CSV header/data found')
    session.summary['metadata']['gap_threshold_us']=inferred_gap if inferred_gap is not None else maxgap*1000
    session.diagnostic('Legacy time/gap metadata is not a fresh-sample guarantee; no checksum available')


def load(source, database, options=None):
    session=Session(database)
    try:
        lines=Lines(source); first=lines.read()
        if first.startswith((b'LYLI',b'RFL2')): raise c.Unsupported('Binary family recognized; verified LYLI/R3 adapters are P8')
        if first.startswith(b'# R1S3_LOG'): native(lines,first,session)
        else: legacy(lines,first,session,options or {})
        session.summary['source_bytes']=lines.offset
        return session.finish()
    except Exception:
        session.close()
        raise
