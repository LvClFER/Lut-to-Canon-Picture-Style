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
    legacy_boundary = source.find("if (!armed) return", start)
    dynamic_boundary = source.find("if (!armed ||", start)
    candidates = [value for value in (legacy_boundary, dynamic_boundary) if value >= 0]
    if not candidates:
        raise RuntimeError("Camera agent no longer has a fail-closed armed-state boundary")
    end = min(candidates)
    observation = source[start:end]
    if "args[3] =" in observation or "args[4] =" in observation or "writeByteArray" in observation:
        raise RuntimeError("Unsafe 0x00000115 mutation detected in the camera agent")
    if "this.prop === 0x01000203" not in source and "this.prop !== 0x01000203" not in source:
        raise RuntimeError("Camera agent does not guard the 0x01000203 transaction")
    if "armdynamic" in source:
        required = (
            "EdsCfpCreateRef", "EdsCfpGetPropertySize", "EdsCfpGetPropertyData",
            "sameArmedPath", "targetRefs", "currentValidation",
            "resolveAcceptanceSymbols", "semantic-signatures-v1", "installAcceptanceHooks",
            "patch-only-the-selected-pf3-inside-edscfparse",
            "original-canon-buffer-observation-only",
            "in-place-canon-compiler-acceptance", "stock-canon-direct",
            "compiler_validation_pass", "compiler_validation_failed",
            "transportMutation: false", "argumentsModified: false", "payloadReplaced: false",
            "compilerGridPathSeen", "dense10IndicesApplied", "dense17IndicesApplied",
            "Unsupported EdsCFParse semantic signature",
        )
        missing = [value for value in required if value not in source]
        if missing:
            raise RuntimeError("Dynamic camera agent is missing safety guards: " + ", ".join(missing))
        if "this.n !== 16752" in source:
            raise RuntimeError("Dynamic camera agent still contains an EOS RP-only payload-size guard")
        if "args[3] =" in source or "args[4] =" in source:
            raise RuntimeError("Dynamic camera agent mutates Canon EDSDK transport arguments")
        if "module.size !==" in source or "base.add(0x" in source:
            raise RuntimeError("Dynamic camera agent still depends on one fixed EdsCFParse build")
        forbidden = (
            "armedLegacyBlock1", "legacyBlock1Hex", "legacy-dual-8192-block-carrier",
            "MODERN_1F00_ENCODER", "patchPayloadNameDetected", "payload_patched",
            "buildCanonNativeCarrier", "compileForNativeCarrier", "validateNativeRoundTrip",
            "api.Set(ref, 0x01000203",
        )
        present = [value for value in forbidden if value in source]
        if present:
            raise RuntimeError("Dynamic camera agent still contains model-specific payload logic: " + ", ".join(present))
    elif "this.n !== 16752" not in source:
        raise RuntimeError("Legacy EOS RP agent does not enforce its validated 16752-byte contract")
    if "!isUserDefSlot" not in source or "this.param !== selectedParam" in source:
        raise RuntimeError("Camera agent does not use dynamic EOS Utility User Def. slot selection")
