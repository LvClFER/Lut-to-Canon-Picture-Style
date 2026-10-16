"""Independent translation of observed MLib math; numeric modes are not camera IDs."""
import argparse
import json
import math
from pathlib import Path

# Coefficients read from 1000's static branches, confirmed with primary vectors.
MATRICES = {
    1: ((.4124, .3576, .1805), (.2126, .7152, .0722), (.0193, .1192, .9505)),
    2: ((.5767, .1856, .1882), (.2973, .6274, .0753), (.027, .0707, .9913)),
    7: ((.7165, .101, .1467), (.2587, .7247, .0166), (0., .0511, .7738)),
    10: ((.436, .3851, .1431), (.2225, .7169, .0606), (.0139, .0971, .7139)),
    11: ((.6097, .2053, .1492), (.3111, .6257, .0632), (.0194, .0609, .7446)),
    0: ((.8956, -.0565, .1114), (.3234, .7132, -.0366), (0., 0., 1.089)),
}
INVERSE_MATRICES = {
    1: ((3.240625477, -1.537207972, -.498628599),
        (-.968930715, 1.875756061, .041517524), (.05571012, -.204021051, 1.056995942)),
    2: ((2.041444561, -.56507087, -.344648472),
        (-.968980596, 1.875853983, .041471142), (.013505422, -.118396008, 1.015205789)),
    7: ((1.462299587, -.184529008, -.273269796),
        (-.522795647, 1.447943878, .068051503), (.034524241, -.095618935, 1.287829631)),
    10: ((3.134577745, -1.617305711, -.491034247),
         (-.978956598, 1.916217746, .033570379), (.072119422, -.229141608, 1.405751075)),
    11: ((1.962643572, -.610736313, -.341428802),
         (-.978753238, 1.916092058, .033485046), (.02891591, -.140802742, 1.349159924)),
    0: ((1.085517171, .085995121, -.108153527),
        (-.492226939, 1.363136817, .096166105), (0., 0., .918273646)),
}


def decode_channel(value):
    if not math.isfinite(value):
        raise ValueError("Finite research samples required")
    if value > .04045:
        return ((value + .055) / 1.055) ** 2.4
    if value > -.04045:
        return value / 12.92
    return -((.055 - value) / 1.055) ** 2.4


def forward_color(rgb, mode):
    if len(rgb) != 3:
        raise ValueError("Need exactly three components")
    linear = [decode_channel(value) for value in rgb]
    matrix = MATRICES.get(1 if mode == 12 else mode, MATRICES[0])
    if mode in (10, 11):
        # Observed scalar SSE additions; Python3.12+ sum may compensate floats.
        products = [[coefficient * value for coefficient, value in zip(row, linear)] for row in matrix]
        return [(terms[0] + terms[1]) + terms[2] for terms in products]
    return [sum(coefficient * value for coefficient, value in zip(row, linear)) for row in matrix]


def inverse_color(xyz, mode):
    if len(xyz) != 3 or not all(math.isfinite(v) for v in xyz):
        raise ValueError("Require three finite components")
    linear = [sum(coefficient * value for coefficient, value in zip(row, xyz))
              for row in INVERSE_MATRICES.get(mode, INVERSE_MATRICES[0])]
    encoded = [12.92 * value if value <= .0031308 else 1.055 * value ** (1 / 2.4) - .055 for value in linear]
    return [max(0., value) for value in encoded], (0xffffffff if any(value < 0 for value in encoded) else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.report.read_text(encoding="utf-8"))
    rows = []
    for row in source["rows"]:
        expected = forward_color(row["input"], row["mode"])
        error = max(abs(a - b) for a, b in zip(row["forward"], expected))
        rows.append({"mode": row["mode"], "input": row["input"], "maxAbsoluteError": error,
                     "within1eMinus14": error <= 1e-14})
    result = {"cases": len(rows), "passed": sum(row["within1eMinus14"] for row in rows),
              "maxError": max(row["maxAbsoluteError"] for row in rows),
              "cameraCompatibilityEstablished": False, "rows": rows}
    inverse_rows = []
    for row in source["rows"]:
        expected, rc = inverse_color(row["forward"], row["mode"])
        error = max(abs(a - b) for a, b in zip(row["inverse"], expected))
        inverse_rows.append({"mode": row["mode"], "maxAbsoluteError": error,
            "rcMatches": rc == row["rcInverse"], "within1eMinus14": error <= 1e-14})
    result["inverseChecks"] = inverse_rows
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({**{key: result[key] for key in ("cases", "passed", "maxError")},
        "inverseCases": len(inverse_rows), "inversePassed": sum(row["within1eMinus14"] and row["rcMatches"] for row in inverse_rows)}))


if __name__ == "__main__":
    main()
