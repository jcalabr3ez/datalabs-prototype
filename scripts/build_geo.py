#!/usr/bin/env python3
"""Build Albers USA state SVG and Massachusetts town SVG.

States: Census cartographic boundaries via us-atlas states-albers-10m
(same Albers USA family as the Florida county map). Towns: Census
cb_2024_25_cousub_500k county subdivisions, projected locally.

Does not touch the Florida county SVG or the tax-atlas tile grid.
"""
from __future__ import annotations

import io
import json
import math
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

FIPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}

ATLAS = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-albers-10m.json"
COUSUB = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_25_cousub_500k.zip"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Pioneer-DataLabs/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def decode_arcs(topo):
    tr = topo["transform"]
    sx, sy = tr["scale"]
    tx, ty = tr["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def ring_from(arc_ids, decoded):
    pts = []
    for idx in arc_ids:
        seq = decoded[~idx][::-1] if idx < 0 else decoded[idx]
        if pts:
            seq = seq[1:]
        pts.extend(seq)
    return pts


def geom_rings(geom, decoded):
    rings = []
    kind = geom.get("type")
    arcs = geom.get("arcs") or []
    if kind == "Polygon":
        for ring in arcs:
            rings.append(ring_from(ring, decoded))
    elif kind == "MultiPolygon":
        for poly in arcs:
            for ring in poly:
                rings.append(ring_from(ring, decoded))
    return rings


def path_d(rings):
    parts = []
    for ring in rings:
        if len(ring) < 3:
            continue
        d = "M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in ring) + "Z"
        parts.append(d)
    return " ".join(parts)


def centroid(rings):
    if not rings or not rings[0]:
        return 0, 0
    ring = rings[0]
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def write_states_svg():
    topo = json.loads(fetch(ATLAS).decode("utf-8"))
    decoded = decode_arcs(topo)
    geoms = topo["objects"]["states"]["geometries"]
    paths = []
    dc_xy = (820, 248)
    for g in geoms:
        fid = str(g.get("id") or "").zfill(2)
        st = FIPS.get(fid)
        if not st:
            continue
        rings = geom_rings(g, decoded)
        d = path_d(rings)
        if not d:
            continue
        name = (g.get("properties") or {}).get("name") or st
        paths.append(
            f'<path class="st" data-st="{st}" data-name="{name}" d="{d}"/>'
        )
        if st == "DC":
            cx, cy = centroid(rings)
            dc_xy = (cx, cy)
    # Labeled square so DC stays readable next to Maryland.
    sq = 14
    x, y = dc_xy[0] + 18, dc_xy[1] - 6
    dc_square = (
        f'<rect class="st st-dc" data-st="DC" data-name="District of Columbia" '
        f'x="{x:.1f}" y="{y:.1f}" width="{sq}" height="{sq}"/>'
        f'<text class="dc-lab" x="{x + sq / 2:.1f}" y="{y + sq + 11:.1f}">DC</text>'
    )
    svg = (
        '<!-- Census cartographic boundaries, Albers USA via us-atlas states-albers-10m. -->\n'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 610" '
        'class="usmap-svg" role="img" aria-label="United States">\n'
        + "\n".join(paths)
        + "\n"
        + dc_square
        + "\n</svg>\n"
    )
    dest = ASSETS / "us-states.svg"
    dest.write_text(svg, encoding="utf-8")
    print(f"wrote {dest} ({len(paths)} states)")


def albers_xy(lon, lat, lon0=-71.8, lat0=42.2, lat1=41.5, lat2=42.6, scale=4200):
    """Local Albers equal-area for Massachusetts, SVG y down."""
    lon = math.radians(lon)
    lat = math.radians(lat)
    lon0 = math.radians(lon0)
    lat0 = math.radians(lat0)
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    n = 0.5 * (math.sin(p1) + math.sin(p2))
    c = math.cos(p1) ** 2 + 2 * n * math.sin(p1)
    r0 = math.sqrt(c - 2 * n * math.sin(lat0)) / n
    theta = n * (lon - lon0)
    r = math.sqrt(c - 2 * n * math.sin(lat)) / n
    x = r * math.sin(theta) * scale
    y = (r0 - r * math.cos(theta)) * scale
    return x, y


def shp_rings(shape):
    pts = list(shape.points)
    starts = list(shape.parts) + [len(pts)]
    rings = []
    for i in range(len(starts) - 1):
        chunk = pts[starts[i]:starts[i + 1]]
        if len(chunk) >= 3:
            rings.append([(p[0], p[1]) for p in chunk])
    return rings


def write_towns_svg():
    import shapefile  # pyshp

    raw = fetch(COUSUB)
    zf = zipfile.ZipFile(io.BytesIO(raw))
    names = {n.split("/")[-1]: n for n in zf.namelist()}
    stem = next(n[:-4] for n in names if n.endswith(".shp"))
    shp = io.BytesIO(zf.read(names[stem + ".shp"]))
    dbf = io.BytesIO(zf.read(names[stem + ".dbf"]))
    shx = io.BytesIO(zf.read(names[stem + ".shx"]))
    r = shapefile.Reader(shp=shp, dbf=dbf, shx=shx)
    fields = [f[0] for f in r.fields[1:]]
    recs = []
    xs, ys = [], []
    for sr in r.shapeRecords():
        rec = dict(zip(fields, sr.record))
        name = rec.get("NAME") or rec.get("NAMELSAD") or ""
        if rec.get("LSAD") in ("00",):  # skip county leftovers if any
            pass
        rings = []
        for ring in shp_rings(sr.shape):
            proj = [albers_xy(lon, lat) for lon, lat in ring]
            rings.append(proj)
            for x, y in proj:
                xs.append(x)
                ys.append(y)
        recs.append((name, rec.get("GEOID") or "", rings))
    if not xs:
        raise SystemExit("no town rings")
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    pad = 18
    w = (maxx - minx) + 2 * pad
    h = (maxy - miny) + 2 * pad

    def tx(x, y):
        return x - minx + pad, (maxy - y) + pad  # flip y

    paths = []
    for name, geoid, rings in recs:
        shifted = [[tx(x, y) for x, y in ring] for ring in rings]
        d = path_d(shifted)
        if not d:
            continue
        slug = name.replace('"', "")
        paths.append(
            f'<path class="town" data-name="{slug}" data-geoid="{geoid}" d="{d}"/>'
        )
    svg = (
        "<!-- Census 2024 MA county subdivisions (cousub 500k), local Albers. -->\n"
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h:.1f}" '
        'class="townmap-svg" role="img" aria-label="Massachusetts cities and towns">\n'
        + "\n".join(paths)
        + "\n</svg>\n"
    )
    dest = ASSETS / "ma-towns.svg"
    dest.write_text(svg, encoding="utf-8")
    print(f"wrote {dest} ({len(paths)} towns)")


def main():
    ASSETS.mkdir(exist_ok=True)
    write_states_svg()
    write_towns_svg()


if __name__ == "__main__":
    main()
