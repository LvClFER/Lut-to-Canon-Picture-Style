"""Independent translation of observed f490 point normalization, not interpolation."""
import struct
import argparse
import json
from pathlib import Path


def normalize_curve(api_bytes):
    if len(api_bytes) < 4:
        raise ValueError("Missing curve count")
    count = struct.unpack_from("<I", api_bytes)[0]
    if not 1 <= count <= 12 or len(api_bytes) < 4 + count * 8:
        raise ValueError("Invalid curve count/length")
    points = struct.unpack_from(f"<{count * 2}I", api_bytes, 4)
    divisor = points[-2]
    if divisor == 0:
        raise ValueError("Zero final abscissa")
    normalized = [value / divisor for value in points]
    # Observed f490 enforces last normalized X >= 1. Here it is exactly 1.
    return struct.pack(f"<{count * 2}d", *normalized), divisor + 1


def verify_trace(row):
    captures = row["mlibCalls"]["captures"]
    actual = {(item["normalizedPairsFloat64Hex"], item["domainSize"])
              for item in captures if item["functionRva"] == "0x1dc90"}
    expected = set()
    for item in captures:
        if item["functionRva"] == "0xf490":
            data, domain = normalize_curve(bytes.fromhex(item["inputPairsHex"]))
            expected.add((data.hex(), domain))
    missing = expected - actual
    return {"model": row["model"], "source": row["source"], "cameraId": row["cameraId"],
            "expectedDistinct": len(expected), "observedDistinct": len(actual),
            "missingIndependentResults": sorted(missing),
            "exactForAllCapturedInputs": bool(expected) and not missing,
            "fullInterpolationValidated": False}


def verify_two_point_samples(row):
    checks = []
    for item in row["mlibCalls"]["captures"]:
        if item["functionRva"] != "0x1dc90" or "sampledPairsFloat64Hex" not in item:
            continue
        if item["curveCount"] != 2:
            continue
        x0, y0, x1, y1 = struct.unpack("<4d", bytes.fromhex(item["normalizedPairsFloat64Hex"]))
        if x0 != 0 or x1 != 1:
            continue
        domain = item["domainSize"]
        actual = bytes.fromhex(item["sampledPairsFloat64Hex"])
        values = struct.unpack(f"<{domain * 2}d", actual)
        expected = [value for i in range(domain)
                    for value in (float(i), y0 + (y1 - y0) * (i / (domain - 1)))]
        errors = [abs(a - b) for a, b in zip(values, expected)]
        checks.append({"domain": domain, "endpointY": y1, "samples": domain,
                       "maxAbsoluteError": max(errors), "within1eMinus14": max(errors) <= 1e-14,
                       "byteExact": actual == struct.pack(f"<{domain * 2}d", *expected)})
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    rows = []
    for row in trace["files"]:
        if "error" in row:
            rows.append({"error": row["error"], "exactForAllCapturedInputs": False})
        else:
            result = verify_trace(row)
            result["twoPointSampleChecks"] = verify_two_point_samples(row)
            rows.append(result)
    report = {"cases": len(rows), "passed": sum(row["exactForAllCapturedInputs"] for row in rows), "rows": rows}
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"cases": report["cases"], "passed": report["passed"]}))


if __name__ == "__main__":
    main()
