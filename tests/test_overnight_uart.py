"""Failure guards for the opt-in overnight hardware runner; no hardware I/O."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import overnight_uart as night


class FakeDevice:
    def __init__(self, state):
        self.state = state
        self.commands = []

    def request(self, command):
        self.commands.append(command)
        if command == 'STATE':
            return dict(self.state)
        raise TimeoutError('Ambiguous control response')


class OvernightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name)
        self.initial = dict(boot='one', revision=1, config_hex='initial', generation='3',
            recording_state='READY', uptime_ms=1000, sample_id=50, missed_samples=0,
            invalid_samples=0, i2c_errors=0, recording_overflows=0, heap_free=100000,
            psram_free=16000000)
        self.device = FakeDevice(dict(self.initial))
        self.run = night.Endurance(self.device, self.out, self.initial, 1)

    def tearDown(self):
        for handler in list(self.run.events.handlers):
            handler.close()
            self.run.events.removeHandler(handler)
        self.temp.cleanup()

    def test_control_timeout_is_never_replayed(self):
        with self.assertRaises(TimeoutError):
            self.run.command('START')
        self.assertEqual(self.device.commands, ['STATE', 'DO one 1 START'])

    def test_cleanup_preserves_external_configuration(self):
        self.device.state['config_hex'] = 'owner-change'
        with self.assertRaisesRegex(RuntimeError, 'externally'):
            self.run.cleanup()
        self.assertEqual(self.device.commands, ['STATE'])

    def test_cleanup_does_not_stop_a_different_recording(self):
        self.run.record_path = '/records/ours.part'
        self.device.state.update(recording_state='RUNNING', recording_path='/records/other.part')
        with self.assertRaisesRegex(RuntimeError, 'different recording'):
            self.run.cleanup()
        self.assertEqual(self.device.commands, ['STATE'])

    def test_reset_is_reported_without_auto_reset(self):
        self.device.state['boot'] = 'new-boot'
        with self.assertRaisesRegex(RuntimeError, 'Unexpected ESP32 reboot'):
            self.run.state()
        self.assertEqual(self.device.commands, ['STATE'])

    def test_lost_samples_fail_health_check(self):
        self.run.measure_base = dict(self.initial)
        self.device.state['missed_samples'] = 1
        with self.assertRaisesRegex(RuntimeError, 'counter increased'):
            self.run.state()

    def test_stop_file_prevents_next_operation(self):
        (self.out / 'STOP').touch()
        with self.assertRaises(InterruptedError):
            self.run.check_stop()
        self.assertEqual(self.device.commands, [])

    def test_corrupted_record_is_rejected(self):
        fixture = night.ROOT / 'tests/fixtures/native-sign-crossing.csv'
        path = self.out / 'bad.csv'
        data = fixture.read_bytes()
        # Retain valid JSON/byte structure but invalidate the recorded final digest.
        head, tail = data.rsplit(b'# END ', 1)
        end = json.loads(tail)
        end['sha256'] = '0' * 64
        path.write_bytes(head + b'# END ' + json.dumps(end).encode() + b'\n')
        with self.assertRaisesRegex(ValueError, 'END count/digest/status mismatch'):
            night.validate_record(path)


if __name__ == '__main__':
    unittest.main()
