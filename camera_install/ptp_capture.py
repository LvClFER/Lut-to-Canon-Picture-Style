"""Validate the observed EOS RP WPD/EDSDK registration relationship.

The Windows capture is a WPD serialization, *not* a raw USB packet. This
module never sends a camera command and never builds or replays 0x00000115.
It is intentionally RP/slot-1-specific until other bodies and slots have
their own independent transport captures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def build_canon_property_packet(property_code: int, value: bytes) -> bytes:
    """Build the data phase used by Canon EOS SetDevicePropValueEx (0x9110)."""
    if not 0 <= property_code <= 0xFFFFFFFF:
        raise ValueError("Canon property code must be an unsigned 32-bit integer")
    value = bytes(value)
    if not value or len(value) > 1024 * 1024:
        raise ValueError("Canon property value has an invalid size")
    # Canon's length field includes the four-byte length word itself. The
    # complete event-style record also includes property code and data length.
    return struct.pack("<III", len(value) + 12, property_code, len(value) + 4) + value


def build_rp_d170_packet(carrier203: bytes) -> bytes:
    """Repack one validated 16,752-byte RP carrier as the D170 data phase."""
    carrier203 = bytes(carrier203)
    if len(carrier203) != 16752:
        raise ValueError("EOS RP D170 requires the validated 16,752-byte carrier")
    # The exact transform is established by five independent RP captures.
    return build_canon_property_packet(0xD170, carrier203[:4] + carrier203[40:])


def build_rp_d163_packet(selector114: bytes, control115: bytes) -> bytes:
    """Recreate captured RP D163 framing without modifying camera-owned state."""
    selector114 = bytes(selector114)
    control115 = bytes(control115)
    if len(selector114) != 4 or len(control115) != 32:
        raise ValueError("EOS RP D163 requires 4-byte selector and 32-byte live control")
    return build_canon_property_packet(
        0xD163, struct.pack("<I", 1) + selector114 + control115,
    )


def _fields(data: bytes, offsets: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(struct.unpack_from("<I", data, offset)[0] for offset in offsets)


def validate_rp_slot1_capture(
    carrier203: bytes,
    selector114: bytes,
    control115: bytes,
    wpd_style: bytes,
    wpd_state: bytes,
) -> dict:
    """Check captured *inputs* byte-for-byte; disclose only metadata/hashes."""
    expected = (16752, 4, 32, 17126, 450)
    actual = tuple(map(len, (carrier203, selector114, control115, wpd_style, wpd_state)))
    if actual != expected:
        raise ValueError(f"Unsupported capture sizes {actual}; expected RP slot-1 {expected}")
    if _fields(wpd_style, (288, 292, 296, 300)) != (16728, 16728, 0xD170, 16720):
        raise ValueError("Unexpected RP WPD style framing")
    if _fields(wpd_state, (288, 292, 296, 300, 304)) != (52, 52, 0xD163, 44, 1):
        raise ValueError("Unexpected RP WPD User Def. 1 framing")
    # Canon's EDSDK carrier is repacked for the WPD property value. The
    # 36-byte slice at 4:40 must not be blindly sent as part of that value.
    if wpd_style[292:17020] != build_rp_d170_packet(carrier203):
        raise ValueError("D170 data does not match the captured EDSDK carrier transform")
    if wpd_state[292:344] != build_rp_d163_packet(selector114, control115):
        raise ValueError("D163 data does not match the captured live EDSDK state")
    return {
        "family": "RP-16752",
        "slot": 1,
        "wpdRepresentation": "Windows Portable Devices input, not USB wire format",
        "styleProperty": "0xD170",
        "stateProperty": "0xD163",
        "carrierSize": len(carrier203),
        "styleDataSize": 16716,
        "selector114Sha256": hashlib.sha256(selector114).hexdigest(),
        "control115Sha256": hashlib.sha256(control115).hexdigest(),
        "control115Policy": "observed only; never copied into a new transaction",
        "exactMatch": True,
    }


def validate_rp_archive(directory: Path) -> list[dict]:
    """Read the five registrations in the V25 research archive, if present."""
    directory = Path(directory)

    def read(pattern: str) -> bytes:
        matches = list(directory.glob(pattern))
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one file matching {pattern}; got {len(matches)}")
        return matches[0].read_bytes()

    results = []
    for index in range(5):
        command_style_index = 1 + 8 * index
        style_index = 2 + 8 * index
        command_state_index = 4 + 8 * index
        state_index = 5 + 8 * index
        carrier_index = 2 + 3 * index
        selector_index = 1 + 3 * index
        control_index = 3 + 3 * index
        for command_index in (command_style_index, command_state_index):
            command = read(f"*NtDeviceIoControlFile_in_{command_index:05d}_0040c108_302.bin")
            if len(command) != 302 or struct.unpack_from("<H", command, 116)[0] != 0x9110:
                raise ValueError(f"Registration {index + 1} did not use Canon PTP 0x9110")
        result = validate_rp_slot1_capture(
            read(f"*EdsSetPropertyData_{carrier_index:05d}_01000203_16752.bin"),
            read(f"*EdsSetPropertyData_{selector_index:05d}_00000114_4.bin"),
            read(f"*EdsSetPropertyData_{control_index:05d}_00000115_32.bin"),
            read(f"*NtDeviceIoControlFile_in_{style_index:05d}_0040c108_17126.bin"),
            read(f"*NtDeviceIoControlFile_in_{state_index:05d}_0040c108_450.bin"),
        )
        result["observedPtpCommand"] = "0x9110"
        result["registration"] = index + 1
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate archived RP WPD inputs without camera access")
    parser.add_argument("archive", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(validate_rp_archive(args.archive), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
