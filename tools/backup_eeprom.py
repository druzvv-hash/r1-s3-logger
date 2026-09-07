"""Read-only EEPROM backup over the firmware's EEPROM DUMP command."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time
import zlib
import serial


def capture(port):
    port.write(b"EEPROM DUMP\n")
    deadline = time.monotonic() + 20
    data = bytearray()
    expected = None
    while time.monotonic() < deadline:
        line = port.readline().decode("ascii", errors="replace").strip()
        if line.startswith("EEPROM BEGIN "):
            _, _, size, checksum = line.split()
            if int(size) != 4096 or expected is not None:
                raise ValueError("Unexpected dump header")
            expected = int(checksum, 16)
        elif line.startswith("EEPROM HEX "):
            match = re.fullmatch(r"EEPROM HEX ([0-9A-F]{4}) ([0-9A-F]{64})", line)
            if not match or expected is None or int(match[1], 16) != len(data):
                raise ValueError("Missing, duplicate or malformed dump line")
            data.extend(bytes.fromhex(match[2]))
        elif line == "EEPROM END":
            if len(data) != 4096 or zlib.crc32(data) != expected:
                raise ValueError("EEPROM length/CRC mismatch")
            return bytes(data)
        elif line.startswith("EEPROM DUMP ERROR"):
            raise ValueError(line)
    raise TimeoutError("No complete EEPROM dump; no backup written")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Private output .bin; must not exist")
    parser.add_argument("--port", default="COM5")
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".json").exists():
        parser.error("Backup or manifest already exists")
    with serial.Serial(port=None, baudrate=115200, timeout=0.5) as port:
        port.dtr = False
        port.rts = False
        port.port = args.port
        port.open()
        port.reset_input_buffer()
        first = capture(port)
        second = capture(port)
    if first != second:
        raise ValueError("Two independently requested dumps disagree")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as out:
        out.write(first)
    manifest = dict(bytes=len(first), crc32=f"{zlib.crc32(first):08X}",
                    sha256=hashlib.sha256(first).hexdigest(), matching_dumps=2,
                    method="EEPROM DUMP; two reads per dump; no EEPROM writes")
    with args.output.with_suffix(".json").open("x", encoding="utf-8") as out:
        json.dump(manifest, out, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
