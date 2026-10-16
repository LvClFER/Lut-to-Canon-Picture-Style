"""Independent candidate for Canon's sampled quadratic B-spline (research only)."""
import argparse
import json
import struct
from pathlib import Path
import numpy as np


def quadratic_samples(points, domain):
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or not 3 <= len(points) <= 12:
        raise ValueError("Expected 3..12 normalized point pairs")
    x, y = points.T
    if x[0] != 0 or x[-1] != 1 or not np.all(np.diff(x) > 0) or not np.isfinite(points).all():
        raise ValueError("Require finite, strictly increasing normalized X from 0 to 1")
    if not 2 <= domain <= 512:
        raise ValueError("Bounded research domain required")
    # Observed 1f450: order=3; interior knot j is midpoint of X[j], X[j+3],
    # not the standard adjacent-X averaging convention.
    knots = [x[0]] * 3 + [(x[j] + x[j + 3]) / 2 for j in range(len(x) - 3)] + [x[-1]] * 3

    def basis(i, degree, z):
        if degree == 0:
            return float(knots[i] <= z < knots[i + 1])
        left_width = knots[i + degree] - knots[i]
        right_width = knots[i + degree + 1] - knots[i + 1]
        left = 0 if left_width == 0 else (z - knots[i]) / left_width * basis(i, degree - 1, z)
        right = 0 if right_width == 0 else (knots[i + degree + 1] - z) / right_width * basis(i + 1, degree - 1, z)
        return left + right

    def row(z):
        return [0.] * (len(x) - 1) + [1.] if z == x[-1] else [basis(i, 2, z) for i in range(len(x))]

    controls = np.linalg.solve(np.array([row(z) for z in x]), y)
    return np.array([np.dot(row(z), controls) for z in np.arange(domain) / (domain - 1)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    checks = []
    for experiment in report.get("experiments", report.get("files", [])):
        if "error" in experiment:
            checks.append({"error": experiment["error"], "within1eMinus14": False}); continue
        for capture in experiment["mlibCalls"]["captures"]:
            if capture["functionRva"] != "0x1dc90" or capture["curveCount"] < 3:
                continue
            count, domain = capture["curveCount"], capture["domainSize"]
            points = np.array(struct.unpack(f"<{count * 2}d", bytes.fromhex(capture["normalizedPairsFloat64Hex"]))).reshape(-1, 2)
            actual = np.array(struct.unpack(f"<{domain * 2}d", bytes.fromhex(capture["sampledPairsFloat64Hex"])))[1::2]
            expected = quadratic_samples(points, domain)
            error = float(np.max(np.abs(actual - expected)))
            checks.append({"name": experiment.get("name", experiment.get("source")), "model": experiment.get("model"), "points": count, "samples": domain,
                           "maxAbsoluteError": error, "byteExactY": actual.tobytes() == expected.tobytes(),
                           "within1eMinus14": error <= 1e-14})
    result = {"onlyPreFinalizationSamplesValidated": True, "cameraAccess": False, "checks": checks}
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(checks))


if __name__ == "__main__":
    main()
