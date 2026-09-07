import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'viewer'))
import core
import server


HEADER=b'timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd\n'


class Viewer(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.sessions=[];self.counter=0

    def tearDown(self):
        for session in self.sessions:session.close()
        self.tmp.cleanup()

    def read(self,raw,options=None):
        self.counter+=1
        session=core.load(io.BytesIO(raw),Path(self.tmp.name)/f'{self.counter}.db',options)
        self.sessions.append(session);return session

    def fixture(self,name,options=None):
        return self.read((ROOT/'tests/fixtures'/name).read_bytes(),options)

    def rows(self,s):
        return [json.loads(row[0]) for row in s.db.execute('SELECT payload FROM samples ORDER BY n')]

    def test_native_matches_reference_all_fixtures(self):
        for path in (ROOT/'tests/fixtures').glob('native-*.csv'):
            raw=path.read_bytes()
            try: expected=core.c.read_native(raw)
            except ValueError:
                with self.assertRaises(ValueError):self.read(raw)
                continue
            actual=self.read(raw)
            self.assertEqual(actual.summary['rows'],len(expected['rows']),path.name)
            self.assertEqual(actual.summary['unverified_rows'],len(expected['unverified_rows']))
            self.assertEqual(actual.summary['partial_line'],expected['partial_line'])
            for row,ref in zip(self.rows(actual),expected['rows']):
                for key in core.c.COLUMNS:
                    self.assertEqual(row[key],str(ref[key]) if key in ('seq','t_us') else ref[key])

    def test_comments_bom_crlf_do_not_become_rows(self):
        a=self.fixture('r1-eight.csv');b=self.fixture('r1-bom-crlf.csv')
        self.assertEqual(a.summary['rows'],2);self.assertEqual(b.summary['rows'],1)
        self.assertEqual(a.summary['comments'],1)
        self.assertEqual(self.rows(a)[1]['I_A'],-1)

    def test_missing_and_nan_never_zero(self):
        s=self.fixture('r1-invalid.csv');row=self.rows(s)[0]
        self.assertIsNone(row['I_A']);self.assertIsNone(row['U_V'])
        self.assertEqual(s.summary['invalid_rows'],1)
        self.assertEqual(s.window(0,0,0,['I_A'])['stats']['I_A']['count'],0)

    def test_pss_preserved_and_short_requires_confirmation(self):
        s=self.fixture('r1-pss.csv')
        self.assertIn('Pss_Wh',s.summary['channels']);self.assertNotIn('Wh_net',s.summary['channels'])
        for name in ['r1-short.csv','r1-short-eight.csv','r1-headerless.csv']:
            with self.assertRaises(core.MappingRequired): self.fixture(name)
        s=self.fixture('r1-short.csv',dict(mapping='short'))
        self.assertEqual(self.rows(s)[0]['I_A'],1)
        s=self.fixture('r1-headerless.csv',dict(mapping='headerless-six'))
        self.assertEqual(s.summary['rows'],1)

    def test_reordered_extra_quoted_multiline(self):
        raw=b'U_V,timestamp,I_A,ms_from_start,P_W,Wh_net,Whc,Whd,note,quality\n5,"local,\ntext",1,0,5,0,0,0,"x,y",99\n'
        s=self.read(raw);row=self.rows(s)[0]
        self.assertEqual(row['I_A'],1);self.assertEqual(row['U_V'],5)
        self.assertEqual(row['timestamp'],'local,\ntext');self.assertEqual(row['quality'],0)
        self.assertEqual(row['extra:quality'],99);self.assertIsNone(row['extra:note'])

    def test_semicolon_decimal_comma_explicit(self):
        raw=HEADER.replace(b',',b';')+b'2025-01-01 00:00:00;0;1,25;5,0;6,25;0;0;0\n'
        with self.assertRaises(core.MappingRequired):self.read(raw)
        s=self.read(raw,dict(delimiter=';',decimal_comma=True))
        self.assertEqual(self.rows(s)[0]['I_A'],1.25)

    def test_resets_repeated_headers_and_wrong_width(self):
        raw=HEADER+b't,0,1,5,5,0,0,0\nt,20,1,5,5,0,0,0\nbad,30,1\nt,40,1,5,5,0,0,0\nt,0,-1,5,-5,0,0,0\n'+HEADER+b't,100,1,5,5,0,0,0\n'
        s=self.read(raw)
        self.assertEqual(len(s.summary['segments']),3)
        self.assertEqual(s.summary['skipped_rows'],1)
        result=s.window(0,0,.04,['I_A'])
        self.assertAlmostEqual(result['stats']['I_A']['covered_s'],.02)
        with self.assertRaises(ValueError):s.window(0,0,.04,['I_A','I_A'])
        with self.assertRaisesRegex(ValueError,'1000 time segments'):
            self.read(HEADER+b't,0,1,5,5,0,0,0\n'*1001)

    def test_gap_and_invalid_do_not_integrate(self):
        s=self.fixture('native-gap.csv')
        result=s.window(0,0,.1,['I_A','P_W'])
        self.assertAlmostEqual(result['stats']['I_A']['covered_s'],.02)
        self.assertAlmostEqual(result['stats']['P_W']['negative'],.1/3600)

    def test_native_sign_split_full_resolution(self):
        s=self.fixture('native-sign-crossing.csv')
        result=s.window(0,0,.06,['P_W'],50)['stats']['P_W']
        self.assertAlmostEqual(result['positive'],.125/3600)
        self.assertAlmostEqual(result['negative'],.125/3600)

    def test_peak_preserved_in_bounded_envelope(self):
        raw=HEADER
        raw+=b''.join(f't,{i},{99 if i==513 else 1},5,5,0,0,0\n'.encode() for i in range(2000))
        s=self.read(raw);result=s.window(0,0,1.999,['I_A'],50)
        self.assertEqual(result['stats']['I_A']['max'],99)
        self.assertEqual(max(x['max'] for x in result['envelopes']['I_A']),99)
        self.assertLessEqual(len(result['envelopes']['I_A']),50)

    def test_large_exact_monotonic_and_timezone(self):
        base=9007199254740993
        raw=HEADER+f'2026-09-07 12:00:00,{base//1000}.{base%1000:03},1,5,5,0,0,0\n2026-09-07 12:00:01,{(base+1000)//1000}.{(base+1000)%1000:03},1,5,5,0,0,0\n'.encode()
        s=self.read(raw,dict(utc_offset_min=120));rows=self.rows(s)
        self.assertEqual(rows[0]['t_us'],str(base));self.assertEqual(rows[0]['utc'],'2026-09-07T10:00:00Z')
        self.assertAlmostEqual(s.summary['segments'][0]['duration_s'],.001)

    def test_duplicate_header_binary_and_long_line(self):
        with self.assertRaises(ValueError):self.read(HEADER.rstrip()+b',I_A\n')
        with self.assertRaisesRegex(ValueError,'Header layout changed'):
            self.read(HEADER+b't,0,1,5,5,0,0,0\n'+b'timestamp,ms_from_start,U_V,I_A,P_W,Wh_net,Whc,Whd\n')
        with self.assertRaises(core.c.Unsupported):self.read(b'LYLI\x02\x00')
        with self.assertRaises(ValueError):self.read(b'x'*65537)

    def test_http_load_errors_and_token(self):
        with server.App(('127.0.0.1',0)) as app:
            worker=threading.Thread(target=app.serve_forever,daemon=True);worker.start()
            root=f'http://127.0.0.1:{app.server_address[1]}'
            try:
                with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(root+'/api/summary')
                self.assertEqual(caught.exception.code,403)
                caught.exception.close()
                req=urllib.request.Request(root+'/api/load',data=(ROOT/'tests/fixtures/native-sign-crossing.csv').read_bytes(),headers={'X-Viewer-Token':app.token})
                with urllib.request.urlopen(req) as res:self.assertEqual(json.load(res)['rows'],4)
                req=urllib.request.Request(root+'/api/window?start=0&end=0.06&channels=I_A',headers={'X-Viewer-Token':app.token})
                with urllib.request.urlopen(req) as res:self.assertEqual(json.load(res)['rows'],4)
                req=urllib.request.Request(root+'/api/load',data=b'unknown,layout\n',headers={'X-Viewer-Token':app.token})
                with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(req)
                self.assertEqual(caught.exception.code,422)
                caught.exception.close()
            finally:app.shutdown();worker.join()


if __name__=='__main__':unittest.main()
