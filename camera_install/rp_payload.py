from __future__ import annotations

import hashlib
import re
import unicodedata


LEGACY_SIZE = 16_744
BLOCK_OFFSET = 360
BLOCK_SIZE = 8_192
SECOND_BLOCK_OFFSET = 8_552
RP_PAYLOAD_SIZE = 16_752
RP_BLOCK_OFFSET = 368
NAME_OFFSETS = (8, 44)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(bytes(data)).hexdigest()


def canon_style_name(value, fallback="Picture Style") -> str:
    text = str(value or fallback or "Picture Style").strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = "".join(character if 32 <= ord(character) <= 126 else "_" for character in text)
    return (text.strip() or fallback or "Picture Style")[:31]


def safe_file_stem(value) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", canon_style_name(value))
    return text.strip("._") or "Picture_Style"


def fixed_ascii32(value) -> bytes:
    encoded = canon_style_name(value).encode("ascii", "replace")[:31]
    return encoded + bytes(32 - len(encoded))


def extract_duplicate_block1(legacy: bytes) -> bytes:
    """Validate the known-good compiler oracle layout used by the self-test."""
    block1, block2 = split_legacy_blocks(legacy)
    if block1 != block2:
        raise RuntimeError("Canon compiler returned an unexpected legacy Block1/Block2 layout")
    return block1


def split_legacy_blocks(legacy: bytes) -> tuple[bytes, bytes]:
    data = bytes(legacy)
    if len(data) != LEGACY_SIZE:
        raise RuntimeError(f"Canon compiler returned {len(data)} bytes; expected {LEGACY_SIZE}")
    block1 = data[BLOCK_OFFSET:BLOCK_OFFSET + BLOCK_SIZE]
    block2 = data[SECOND_BLOCK_OFFSET:SECOND_BLOCK_OFFSET + BLOCK_SIZE]
    if len(block1) != BLOCK_SIZE or len(block2) != BLOCK_SIZE:
        raise RuntimeError("Canon compiler returned an incomplete legacy Block1/Block2 layout")
    return block1, block2


def extract_legacy_block1(legacy: bytes) -> bytes:
    """Extract the exact target Block1 used by the validated EOS RP V37 carrier recipe.

    Unlike the known-good Superia compiler self-test, a target PF3 may legitimately
    compile to different Block1 and Block2 values. The physically validated EOS RP
    recipe replaces only Block1 and keeps the carrier's Block2 unchanged.
    """
    block1, _block2 = split_legacy_blocks(legacy)
    return block1


def validate_compiler_selftest(legacy: bytes, expected_block: bytes) -> str:
    expected = bytes(expected_block)
    if len(expected) != BLOCK_SIZE:
        raise RuntimeError("The validated compiler reference is not 8192 bytes")
    actual = extract_duplicate_block1(legacy)
    if actual != expected:
        raise RuntimeError(
            "Canon compiler self-test did not match the validated reference byte-for-byte; "
            "camera installation is blocked"
        )
    return sha256_bytes(actual)


def build_rp_payload(carrier: bytes, block1: bytes, style_name: str) -> bytes:
    source = bytes(carrier)
    block = bytes(block1)
    if len(source) != RP_PAYLOAD_SIZE:
        raise RuntimeError(f"Invalid EOS RP carrier: {len(source)} bytes")
    if len(block) != BLOCK_SIZE:
        raise RuntimeError(f"Invalid compiled Block1: {len(block)} bytes")
    output = bytearray(source)
    output[RP_BLOCK_OFFSET:RP_BLOCK_OFFSET + BLOCK_SIZE] = block
    name = fixed_ascii32(style_name)
    for offset in NAME_OFFSETS:
        output[offset:offset + 32] = name
    if b"TWILIGHT" in output:
        raise RuntimeError("Carrier name replacement failed: TWILIGHT remains in the final payload")
    return bytes(output)


def validate_agent_source(source: str) -> None:
    """Static guard for the critical transaction-property boundary."""
    if "this.prop === 0x00000115" not in source or "untouched: true" not in source:
        raise RuntimeError("Camera agent no longer contains the 0x00000115 observation guard")
    start = source.index("// 0x00000115 is binary state/control data")
    end = source.index("if (!armed) return", start)
    observation = source[start:end]
    if "args[3] =" in observation or "args[4] =" in observation or "writeByteArray" in observation:
        raise RuntimeError("Unsafe 0x00000115 mutation detected in the camera agent")
    if "this.prop === 0x01000203" not in source or "this.n !== 16752" not in source:
        raise RuntimeError("Camera agent does not enforce the validated 0x01000203 payload contract")
    if "if (!isUserDefSlot) return" not in source or "this.param !== selectedParam" in source:
        raise RuntimeError("Camera agent does not use dynamic EOS Utility User Def. slot selection")
