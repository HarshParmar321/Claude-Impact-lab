"""Generate the NagarLens synthetic Mumbai road-repair dataset.

Every entity in this dataset (contractors, complaints, work orders, amounts,
accidents, social posts) is SYNTHETIC. Road and ward names are used only as
geographic labels. Re-running this script with the same seed produces
byte-identical files.

The Sion Trombay Road golden demo case (RD0235, WO25-01483, WO25-02469,
BMC25-003869, BMC25-003870) is inserted with fixed values from the build spec.

Usage:
    python scripts/generate_seed_data.py            # writes to backend/data/
    python scripts/generate_seed_data.py --out DIR
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2025
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

WARDS = [
    # code, name, zone, lat, lon, population, area_sqkm, annual_road_budget_inr, low_lying_share
    ("A", "A Ward (Colaba–Fort)", "City", 18.925, 72.830, 185_000, 12.4, 41_000_000, 0.30),
    ("E", "E Ward (Byculla)", "City", 18.975, 72.835, 393_000, 7.4, 38_000_000, 0.35),
    ("F/N", "F/North Ward (Matunga–Sion)", "City", 19.030, 72.860, 529_000, 12.9, 46_000_000, 0.45),
    ("G/N", "G/North Ward (Dadar–Dharavi)", "City", 19.020, 72.842, 599_000, 9.1, 44_000_000, 0.40),
    ("H/W", "H/West Ward (Bandra West)", "Western Suburbs", 19.060, 72.832, 307_000, 12.8, 43_000_000, 0.25),
    ("K/E", "K/East Ward (Andheri East)", "Western Suburbs", 19.115, 72.865, 823_000, 23.8, 52_000_000, 0.20),
    ("L", "L Ward (Kurla)", "Eastern Suburbs", 19.072, 72.886, 902_000, 15.9, 48_000_000, 0.50),
    ("M/E", "M/East Ward (Govandi–Mankhurd–Trombay)", "Eastern Suburbs", 19.048, 72.925, 807_000, 32.5, 47_000_000, 0.55),
    ("M/W", "M/West Ward (Chembur)", "Eastern Suburbs", 19.058, 72.898, 411_000, 19.0, 40_000_000, 0.35),
    ("N", "N Ward (Ghatkopar)", "Eastern Suburbs", 19.088, 72.912, 622_000, 25.6, 45_000_000, 0.30),
    ("S", "S Ward (Bhandup–Powai)", "Eastern Suburbs", 19.140, 72.930, 743_000, 31.0, 46_000_000, 0.25),
    ("P/N", "P/North Ward (Malad)", "Western Suburbs", 19.185, 72.845, 941_000, 46.7, 50_000_000, 0.30),
]

LOCALITIES = {
    "A": ["Colaba", "Fort", "Cuffe Parade"],
    "E": ["Byculla", "Mazgaon", "Agripada"],
    "F/N": ["Matunga", "Sion", "Wadala"],
    "G/N": ["Dadar", "Mahim", "Dharavi"],
    "H/W": ["Bandra West", "Khar West", "Santacruz West"],
    "K/E": ["Andheri East", "Marol", "Jogeshwari East"],
    "L": ["Kurla", "Saki Naka", "Chandivali"],
    "M/E": ["Govandi", "Mankhurd", "Trombay", "Deonar"],
    "M/W": ["Chembur", "Tilak Nagar", "Chembur Camp"],
    "N": ["Ghatkopar", "Vidyavihar", "Vikhroli"],
    "S": ["Bhandup", "Kanjurmarg", "Powai"],
    "P/N": ["Malad", "Malvani", "Dindoshi"],
}

NAMED_ARTERIALS = {
    "A": ["Shahid Bhagat Singh Road", "Colaba Causeway", "Madame Cama Road"],
    "E": ["Dr. Ambedkar Road (Byculla)", "Sant Savta Marg", "Mazgaon Road"],
    "F/N": ["Sion Circle Approach Road", "Wadala Station Road", "Matunga Road"],
    "G/N": ["Senapati Bapat Marg", "Gokhale Road", "Dharavi 90 Feet Road"],
    "H/W": ["S.V. Road (Bandra)", "Linking Road", "Hill Road"],
    "K/E": ["Andheri–Kurla Road", "Marol Maroshi Road", "Mahakali Caves Road"],
    "L": ["LBS Marg (Kurla)", "Saki Vihar Road", "CST Road (Kurla)"],
    "M/E": ["Ghatkopar–Mankhurd Link Road", "Deonar Farm Road", "Mankhurd Station Road"],
    "M/W": ["Chembur Station Road", "R.C. Marg", "Diamond Garden Road"],
    "N": ["LBS Marg (Ghatkopar)", "M.G. Road (Ghatkopar)", "Vikhroli Station Road"],
    "S": ["JVLR (Powai)", "Bhandup Village Road", "Kanjurmarg Station Road"],
    "P/N": ["Marve Road", "S.V. Road (Malad)", "Dindoshi Link Road"],
}

# Clearly fictional contractor names (synthetic dataset)
CONTRACTORS = [
    ("CT01", "Kestrel Roadworks", "Class I", 2009, 0.92, 0.06, 0.95),
    ("CT02", "Banyan Surface Co.", "Class I", 2012, 0.88, 0.09, 0.90),
    ("CT03", "Monsoon Shield Infra", "Class II", 2015, 0.80, 0.14, 0.80),
    ("CT04", "Coral Road Systems", "Class I", 2007, 0.90, 0.07, 0.93),
    ("CT05", "Lantern Civil Works", "Class II", 2016, 0.74, 0.17, 0.70),
    ("CT06", "Peacock Asphalt Works", "Class II", 2011, 0.85, 0.10, 0.86),
    ("CT07", "Tidewater Paving", "Class I", 2010, 0.84, 0.11, 0.82),
    ("CT08", "Saffron Lane Builders", "Class III", 2019, 0.70, 0.19, 0.62),
    ("CT09", "Basalt Line Engineering", "Class I", 2008, 0.93, 0.05, 0.96),
    ("CT10", "Rainline Constructions", "Class II", 2014, 0.78, 0.13, 0.77),
    ("CT11", "Jacaranda Paving", "Class III", 2020, 0.76, 0.15, 0.68),
    ("CT12", "Mangrove Infra Projects", "Class II", 2013, 0.82, 0.12, 0.84),
    ("CT13", "Copperleaf Civil", "Class III", 2021, 0.72, 0.16, 0.66),
    ("CT14", "Harbourline Surfacing", "Class I", 2006, 0.89, 0.08, 0.91),
]
# columns of quality profile: sla_skill, reopen_base, evidence_skill

RATE_CARD = [
    # id, work_type, repair_method, unit, rate, life_months
    ("RC01", "pothole_patch", "cold_mix", "per sqm", 1450, 6),
    ("RC02", "pothole_patch", "hot_mix", "per sqm", 2600, 18),
    ("RC03", "pothole_patch", "mastic_asphalt", "per sqm", 4600, 36),
    ("RC04", "pothole_patch", "jet_patcher", "per sqm", 1900, 12),
    ("RC05", "surface_restoration", "hot_mix", "per sqm", 1150, 48),
    ("RC06", "surface_restoration", "mastic_asphalt", "per sqm", 3900, 60),
    ("RC07", "trench_reinstatement", "paver_block", "per sqm", 2200, 36),
    ("RC08", "trench_reinstatement", "hot_mix", "per sqm", 2400, 24),
    ("RC09", "drain_cover_replacement", "precast_cover", "per job", 14500, 60),
    ("RC10", "drain_cover_replacement", "ductile_iron_cover", "per job", 26000, 96),
]

METHOD_REOPEN_ADJ = {
    "cold_mix": 0.20, "hot_mix": 0.05, "mastic_asphalt": 0.0, "jet_patcher": 0.07,
    "paver_block": 0.03, "precast_cover": 0.04, "ductile_iron_cover": 0.0,
}

SLA_BY_CLASS = {
    "arterial": ("T1", 2),
    "sub-arterial": ("T2", 4),
    "collector": ("T3", 7),
    "local": ("T3", 7),
}

ROADS_PER_WARD = 30
N_WORK_ORDERS = 2600
GOLDEN_WO_A = "WO25-01483"
GOLDEN_WO_B = "WO25-02469"
GOLDEN_ROAD = "RD0235"
GOLDEN_C_EN = "BMC25-003870"
GOLDEN_C_MR = "BMC25-003869"

START = date(2025, 4, 1)
END = date(2025, 10, 31)


def d2s(d: date | None) -> str:
    return "" if d is None else d.isoformat()


def rand_date(a: date, b: date) -> date:
    return a + timedelta(days=int(rng.integers(0, (b - a).days + 1)))


def monsoon_weighted_date(a: date, b: date) -> date:
    """More complaints and repairs in June–September."""
    while True:
        d = rand_date(a, b)
        w = 1.0 if d.month in (6, 7, 8, 9) else 0.45
        if rng.random() < w:
            return d


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Wards and localities
# ---------------------------------------------------------------------------

def build_wards():
    rows, feats = [], []
    for code, name, zone, lat, lon, pop, area, budget, low in WARDS:
        rows.append(dict(ward_code=code, ward_name=name, zone=zone, population=pop,
                         area_sqkm=area, annual_road_budget_inr=budget,
                         low_lying_share=low, centroid_lat=lat, centroid_lon=lon))
        h = 0.0115
        ring = [[lon - h, lat - h], [lon + h, lat - h], [lon + h, lat + h], [lon - h, lat + h], [lon - h, lat - h]]
        feats.append({"type": "Feature", "properties": {"ward_code": code, "ward_name": name, "synthetic_boundary": True},
                      "geometry": {"type": "Polygon", "coordinates": [ring]}})
    return pd.DataFrame(rows), {"type": "FeatureCollection", "features": feats}


def build_localities(wards_df):
    rows, n = [], 1
    for _, w in wards_df.iterrows():
        for name in LOCALITIES[w.ward_code]:
            rows.append(dict(locality_id=f"LOC{n:03d}", locality_name=name, ward_code=w.ward_code,
                             lat=round(w.centroid_lat + rng.uniform(-0.008, 0.008), 5),
                             lon=round(w.centroid_lon + rng.uniform(-0.008, 0.008), 5)))
            n += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Roads
# ---------------------------------------------------------------------------

def build_roads(wards_df, loc_df):
    rows, feats = [], []
    n = 1
    for _, w in wards_df.iterrows():
        locs = loc_df[loc_df.ward_code == w.ward_code]
        arterial_names = list(NAMED_ARTERIALS[w.ward_code])
        for k in range(ROADS_PER_WARD):
            rid = f"RD{n:04d}"
            loc = locs.iloc[k % len(locs)]
            if k < 3:
                cls = "arterial"
                name = arterial_names[k]
            else:
                cls = rng.choice(["arterial", "sub-arterial", "collector", "local"], p=[0.08, 0.27, 0.33, 0.32])
                style = rng.integers(0, 5)
                if style == 0:
                    name = f"{loc.locality_name} Road No. {k}"
                elif style == 1:
                    name = f"{loc.locality_name} Station Road {k}"
                elif style == 2:
                    name = f"{loc.locality_name} Link Road {k}"
                elif style == 3:
                    name = f"{loc.locality_name} Cross Lane {k}"
                else:
                    name = f"{loc.locality_name} Market Road {k}"
            length = int({"arterial": rng.integers(1800, 4200), "sub-arterial": rng.integers(900, 2200),
                          "collector": rng.integers(400, 1200), "local": rng.integers(150, 600)}[cls])
            width = float({"arterial": rng.choice([18, 24, 30]), "sub-arterial": rng.choice([12, 15, 18]),
                           "collector": rng.choice([9, 12]), "local": rng.choice([6, 7.5, 9])}[cls])
            under_dlp = "Y" if rng.random() < 0.09 else "N"
            best = "Y" if (cls in ("arterial", "sub-arterial") and rng.random() < 0.8) else ("Y" if rng.random() < 0.1 else "N")
            bus_routes = int(rng.integers(4, 16)) if (best == "Y" and cls == "arterial") else (int(rng.integers(1, 7)) if best == "Y" else 0)
            lat0 = loc.lat + rng.uniform(-0.004, 0.004)
            lon0 = loc.lon + rng.uniform(-0.004, 0.004)
            ang = rng.uniform(0, math.pi)
            dlat = (length / 111_000) * math.sin(ang)
            dlon = (length / (111_000 * math.cos(math.radians(lat0)))) * math.cos(ang)
            coords = [[round(lon0, 6), round(lat0, 6)], [round(lon0 + dlon / 2 + rng.uniform(-0.0006, 0.0006), 6), round(lat0 + dlat / 2 + rng.uniform(-0.0006, 0.0006), 6)], [round(lon0 + dlon, 6), round(lat0 + dlat, 6)]]
            surface = rng.choice(["bitumen", "concrete", "paver"], p=[0.68, 0.25, 0.07])
            dlp_end = ""
            dlp_start = ""
            if under_dlp == "Y":
                s = rand_date(date(2023, 6, 1), date(2025, 3, 1))
                dlp_start = d2s(s)
                dlp_end = d2s(s + timedelta(days=365 * 3))
            row = dict(road_id=rid, road_name=name, ward_code=w.ward_code, locality_id=loc.locality_id,
                       road_class=cls, length_m=length, width_m=width, surface_type=surface,
                       under_dlp=under_dlp, dlp_start_date=dlp_start, dlp_end_date=dlp_end,
                       best_bus_route=best, bus_routes_count=bus_routes,
                       low_lying="Y" if rng.random() < w.low_lying_share else "N",
                       condition_index=int(rng.integers(28, 92)),
                       distress_area_sqm=round(float(rng.uniform(2.0, 16.0)), 1),
                       centroid_lat=round(coords[1][1], 6), centroid_lon=round(coords[1][0], 6))
            if rid == GOLDEN_ROAD:
                coords = [[72.9030, 19.0470], [72.9180, 19.0438], [72.9330, 19.0402]]
                row.update(road_name="Sion Trombay Road", road_class="arterial", length_m=3600, width_m=24.0,
                           surface_type="bitumen", under_dlp="Y", dlp_start_date="2024-02-15",
                           dlp_end_date="2027-02-14", best_bus_route="Y", bus_routes_count=15,
                           low_lying="Y", condition_index=41, distress_area_sqm=11.5,
                           centroid_lat=19.0438, centroid_lon=72.9180, locality_id=locs[locs.locality_name == "Trombay"].iloc[0].locality_id)
            rows.append(row)
            feats.append({"type": "Feature", "properties": {"road_id": rid, "road_name": row["road_name"], "ward_code": w.ward_code,
                                                            "road_class": row["road_class"], "under_dlp": row["under_dlp"]},
                          "geometry": {"type": "LineString", "coordinates": coords}})
            n += 1
    return pd.DataFrame(rows), {"type": "FeatureCollection", "features": feats}


# ---------------------------------------------------------------------------
# Context data: traffic, facilities, flood hotspots, rainfall, tides
# ---------------------------------------------------------------------------

def build_traffic(roads_df):
    rows = []
    for _, r in roads_df.iterrows():
        base = {"arterial": 3000, "sub-arterial": 1700, "collector": 800, "local": 300}[r.road_class]
        rows.append(dict(road_id=r.road_id, peak_hour_vehicles=int(base * rng.uniform(0.6, 1.35)),
                         congestion_index=round(float(np.clip(rng.normal({"arterial": 7.2, "sub-arterial": 6.0, "collector": 4.5, "local": 3.0}[r.road_class], 1.2), 1, 10)), 1),
                         bus_routes=int(r.bus_routes_count), two_wheeler_share=round(float(rng.uniform(0.38, 0.62)), 2),
                         survey_date="2025-07-15"))
    df = pd.DataFrame(rows)
    m = df.road_id == GOLDEN_ROAD
    df.loc[m, ["peak_hour_vehicles", "congestion_index", "bus_routes", "two_wheeler_share"]] = [3723, 8.3, 15, 0.53]
    return df


def build_facilities(roads_df, wards_df):
    rows, n = [], 1
    for _, w in wards_df.iterrows():
        wr = roads_df[roads_df.ward_code == w.ward_code]
        for ftype, count in (("hospital", int(rng.integers(2, 5))), ("school", int(rng.integers(5, 10)))):
            for i in range(count):
                road = wr.iloc[int(rng.integers(0, len(wr)))]
                lat = road.centroid_lat + rng.uniform(-0.004, 0.004)
                lon = road.centroid_lon + rng.uniform(-0.004, 0.004)
                rows.append(dict(facility_id=f"FAC{n:03d}", facility_type=ftype,
                                 facility_name=f"{w.ward_code} {'Municipal Hospital' if ftype == 'hospital' else 'Municipal School'} {i + 1}",
                                 ward_code=w.ward_code, lat=round(lat, 6), lon=round(lon, 6)))
                n += 1
    # Golden context: a hospital and two schools near Sion Trombay Road
    for ftype, name, dlat, dlon in (("hospital", "M/E Maternity Home (synthetic)", 0.0021, 0.0012),
                                     ("school", "Trombay Municipal School (synthetic)", -0.0018, 0.0025),
                                     ("school", "Mandala Urdu School (synthetic)", 0.0016, -0.0030)):
        rows.append(dict(facility_id=f"FAC{n:03d}", facility_type=ftype, facility_name=name, ward_code="M/E",
                         lat=round(19.0438 + dlat, 6), lon=round(72.9180 + dlon, 6)))
        n += 1
    df = pd.DataFrame(rows)
    # nearest road + distance (computed against road centroid; synthetic approximation)
    near, dist = [], []
    for _, f in df.iterrows():
        cand = roads_df[roads_df.ward_code == f.ward_code]
        ds = cand.apply(lambda r: haversine_m(f.lat, f.lon, r.centroid_lat, r.centroid_lon), axis=1)
        i = ds.idxmin()
        near.append(cand.loc[i, "road_id"])
        dist.append(int(ds.min()))
    df["nearest_road_id"] = near
    df["distance_m"] = dist
    return df


def build_flood_hotspots(roads_df):
    rows = []
    cand = roads_df[(roads_df.low_lying == "Y")].sample(n=34, random_state=SEED)
    n = 1
    for _, r in cand.iterrows():
        if r.road_id == GOLDEN_ROAD:
            continue
        rows.append(dict(hotspot_id=f"FH{n:03d}", hotspot_name=f"{r.road_name} low point",
                         ward_code=r.ward_code, lat=round(r.centroid_lat + rng.uniform(-0.002, 0.002), 6),
                         lon=round(r.centroid_lon + rng.uniform(-0.002, 0.002), 6),
                         severity=rng.choice(["moderate", "high", "severe"], p=[0.45, 0.4, 0.15]),
                         nearest_road_id=r.road_id, distance_m=int(rng.integers(40, 650)),
                         tide_sensitive="Y" if rng.random() < 0.4 else "N"))
        n += 1
    rows.append(dict(hotspot_id=f"FH{n:03d}", hotspot_name="Sion Trombay Road at Mandala junction",
                     ward_code="M/E", lat=19.0429, lon=72.9221, severity="high",
                     nearest_road_id=GOLDEN_ROAD, distance_m=180, tide_sensitive="Y"))
    return pd.DataFrame(rows)


def build_rainfall(wards_df):
    rows = []
    d = date(2025, 4, 1)
    while d <= END:
        city_base = {4: 0.3, 5: 2.0, 6: 18.0, 7: 32.0, 8: 22.0, 9: 14.0, 10: 3.0}[d.month]
        storm = rng.random() < (0.10 if d.month in (6, 7, 8, 9) else 0.01)
        for _, w in wards_df.iterrows():
            v = max(0.0, rng.gamma(1.2, city_base / 1.2) if city_base > 0 else 0.0)
            if storm:
                v += rng.uniform(60, 160)
            if w.ward_code == "M/E" and d in (date(2025, 8, 7), date(2025, 8, 8), date(2025, 8, 18), date(2025, 8, 19)):
                v = {date(2025, 8, 7): 64.2, date(2025, 8, 8): 41.5, date(2025, 8, 18): 118.6, date(2025, 8, 19): 96.3}[d]
            rows.append(dict(date=d2s(d), ward_code=w.ward_code, rainfall_mm=round(float(v), 1)))
        d += timedelta(days=1)
    return pd.DataFrame(rows)


def build_tides():
    rows = []
    d = date(2025, 4, 1)
    i = 0
    while d <= END:
        h = 3.9 + 0.7 * math.sin(2 * math.pi * i / 14.77) + rng.normal(0, 0.08)
        hh = int(6 + (i * 0.84) % 12)
        rows.append(dict(date=d2s(d), high_tide_time=f"{hh:02d}:{int(rng.integers(0, 60)):02d}",
                         high_tide_m=round(h, 2), high_tide_alert="Y" if h >= 4.5 else "N"))
        d += timedelta(days=1)
        i += 1
    df = pd.DataFrame(rows)
    df.loc[df.date == "2025-08-19", ["high_tide_m", "high_tide_alert"]] = [4.71, "Y"]
    return df


# ---------------------------------------------------------------------------
# Work orders
# ---------------------------------------------------------------------------

def choose_work(road_class: str):
    wt = rng.choice(["pothole_patch", "surface_restoration", "trench_reinstatement", "drain_cover_replacement"],
                    p=[0.66, 0.10, 0.12, 0.12])
    rc = [r for r in RATE_CARD if r[1] == wt]
    if wt == "pothole_patch":
        probs = [0.30, 0.30, 0.20, 0.20] if road_class in ("collector", "local") else [0.15, 0.35, 0.32, 0.18]
        r = rc[int(rng.choice(len(rc), p=probs))]
    else:
        r = rc[int(rng.integers(0, len(rc)))]
    if wt == "pothole_patch":
        area = round(float(rng.uniform(1.2, 14.0)), 1)
    elif wt == "surface_restoration":
        area = round(float(rng.uniform(40, 260)), 1)
    elif wt == "trench_reinstatement":
        area = round(float(rng.uniform(6, 45)), 1)
    else:
        area = 0.0
    return wt, r, area


def build_work_orders(roads_df):
    contractors = {c[0]: c for c in CONTRACTORS}
    # each ward has a preferred contractor pool
    pools = {}
    cids = list(contractors)
    for i, (code, *_rest) in enumerate(WARDS):
        pools[code] = [cids[(i + k) % len(cids)] for k in (0, 1, 3, 5, 8)]
    # ward-level process quality (linkage) and DLP control
    ward_link = {"A": 0.93, "E": 0.86, "F/N": 0.84, "G/N": 0.88, "H/W": 0.94, "K/E": 0.80, "L": 0.74,
                 "M/E": 0.70, "M/W": 0.85, "N": 0.82, "S": 0.78, "P/N": 0.76}
    ward_dlp_control = {"A": 0.65, "E": 0.45, "F/N": 0.40, "G/N": 0.55, "H/W": 0.70, "K/E": 0.35, "L": 0.25,
                        "M/E": 0.20, "M/W": 0.50, "N": 0.40, "S": 0.30, "P/N": 0.30}

    road_weights = roads_df.road_class.map({"arterial": 4.0, "sub-arterial": 2.5, "collector": 1.5, "local": 1.0}).values
    road_weights = road_weights / road_weights.sum()

    recs = []
    n_regular = N_WORK_ORDERS - 2 - 2 * 24  # reserve golden + 24 injected duplicate partners
    for _ in range(n_regular):
        road = roads_df.iloc[int(rng.choice(len(roads_df), p=road_weights))]
        recs.append(make_wo(road, contractors, pools, ward_link, ward_dlp_control))
    # Inject duplicate-like pairs (base + copy without complaint) and some near-misses
    for j in range(24):
        road = roads_df.iloc[int(rng.choice(len(roads_df), p=road_weights))]
        base = make_wo(road, contractors, pools, ward_link, ward_dlp_control, force_paid=True, force_patch=True)
        copy = dict(base)
        copy["has_complaint"] = False
        near_miss = j >= 19  # last five are deliberate near-misses that must NOT trigger the rule
        gap = int(rng.integers(6, 11)) if (near_miss and j % 2 == 0) else int(rng.integers(1, 5))
        copy["issued_date"] = base["completed_date"] + timedelta(days=gap - 1)
        copy["completed_date"] = copy["issued_date"] + timedelta(days=int(rng.integers(0, 2)))
        copy["recorded_date"] = copy["completed_date"]
        copy["area_sqm"] = round(base["area_sqm"] * float(rng.uniform(0.98, 1.02)), 1) if base["area_sqm"] else 0.0
        pct = float(rng.uniform(0.11, 0.18)) if (near_miss and j % 2 == 1) else float(rng.uniform(0.005, 0.055))
        sign = 1 if rng.random() < 0.5 else -1
        copy["cost_inr"] = int(round(base["cost_inr"] * (1 + sign * pct)))
        copy["photo_before"], copy["photo_after"], copy["measurement_book"] = "N", "N", ("Y" if rng.random() < 0.3 else "N")
        copy["reopened_within_30d"] = "N"
        copy["injected"] = "near_miss" if near_miss else "duplicate"
        recs.append(base)
        recs.append(copy)

    df = pd.DataFrame(recs).sort_values(["issued_date", "road_id"], kind="stable").reset_index(drop=True)
    reserved = {1483, 2469}
    ids, k = [], 1
    for _ in range(len(df)):
        while k in reserved:
            k += 1
        ids.append(f"WO25-{k:05d}")
        k += 1
    df["work_order_id"] = ids

    golden = [
        dict(work_order_id=GOLDEN_WO_A, road_id=GOLDEN_ROAD, ward_code="M/E", contractor_id="CT07",
             work_type="pothole_patch", repair_method="mastic_asphalt", rate_card_id="RC03", area_sqm=3.4,
             cost_inr=17181, issued_date=date(2025, 8, 7), completed_date=date(2025, 8, 9),
             recorded_date=date(2025, 8, 9), sla_tier="T1", sla_days=2, reopened_within_30d="N",
             photo_before="Y", photo_after="Y", measurement_book="Y", engineer_certificate="Y",
             billed_to="BMC", has_complaint=True, injected="golden"),
        dict(work_order_id=GOLDEN_WO_B, road_id=GOLDEN_ROAD, ward_code="M/E", contractor_id="CT07",
             work_type="pothole_patch", repair_method="mastic_asphalt", rate_card_id="RC03", area_sqm=3.4,
             cost_inr=16754, issued_date=date(2025, 8, 10), completed_date=date(2025, 8, 10),
             recorded_date=date(2025, 8, 10), sla_tier="T1", sla_days=2, reopened_within_30d="N",
             photo_before="N", photo_after="N", measurement_book="N", engineer_certificate="Y",
             billed_to="BMC", has_complaint=False, injected="golden"),
    ]
    df = pd.concat([df, pd.DataFrame(golden)], ignore_index=True)
    df["sla_met"] = np.where((pd.to_datetime(df.completed_date) - pd.to_datetime(df.issued_date)).dt.days <= df.sla_days, "Y", "N")
    df["payment_status"] = np.where(df.billed_to == "BMC", "BILLED_PENDING_RELEASE", "WARRANTY_EXECUTED_NO_BMC_PAYMENT")
    df = df.sort_values("work_order_id").reset_index(drop=True)
    return df


def make_wo(road, contractors, pools, ward_link, ward_dlp_control, force_paid=False, force_patch=False):
    cid = pools[road.ward_code][int(rng.integers(0, 5))] if rng.random() < 0.85 else list(contractors)[int(rng.integers(0, len(contractors)))]
    _, _, _, _, sla_skill, reopen_base, ev_skill = contractors[cid]
    wt, rc, area = choose_work(road.road_class)
    if force_patch and wt != "pothole_patch":
        rc = [r for r in RATE_CARD if r[1] == "pothole_patch"][int(rng.integers(0, 4))]
        wt = "pothole_patch"
        area = round(float(rng.uniform(1.5, 12.0)), 1)
    expected = area * rc[4] if rc[3] == "per sqm" else rc[4]
    u = rng.random()
    if u < 0.045:
        ratio = rng.uniform(1.42, 2.10)
    elif u < 0.075:
        ratio = rng.uniform(1.31, 1.395)
    elif u < 0.10:
        ratio = rng.uniform(0.45, 0.74)
    else:
        ratio = float(np.clip(rng.normal(1.04, 0.08), 0.78, 1.28))
    cost = int(round(expected * ratio))
    tier, sla_days = SLA_BY_CLASS[road.road_class]
    issued = monsoon_weighted_date(START, END - timedelta(days=10))
    on_time = rng.random() < sla_skill
    dur = int(rng.integers(0, sla_days + 1)) if on_time else sla_days + int(rng.integers(1, 6))
    completed = issued + timedelta(days=dur)
    billed_to = "BMC"
    if road.under_dlp == "Y" and not force_paid and rng.random() < ward_dlp_control[road.ward_code]:
        billed_to = "DLP_CONTRACTOR"
        cost = 0
    reopen_p = reopen_base + METHOD_REOPEN_ADJ[rc[2]] + (0.05 if issued.month in (6, 7, 8) else 0)
    ev = lambda: "Y" if rng.random() < ev_skill else "N"
    return dict(road_id=road.road_id, ward_code=road.ward_code, contractor_id=cid, work_type=wt,
                repair_method=rc[2], rate_card_id=rc[0], area_sqm=area, cost_inr=cost,
                issued_date=issued, completed_date=completed, recorded_date=completed + timedelta(days=int(rng.integers(0, 3))),
                sla_tier=tier, sla_days=sla_days,
                reopened_within_30d="Y" if rng.random() < reopen_p else "N",
                photo_before=ev(), photo_after=ev(), measurement_book=ev(), engineer_certificate="Y" if rng.random() < 0.95 else "N",
                billed_to=billed_to, has_complaint=rng.random() < ward_link[road.ward_code], injected="")


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------

TEXTS = {
    "pothole": {
        "en": ["Big pothole on {road}, two-wheelers are skidding.", "Pothole near the bus stop on {road}, please fix.",
               "Deep pothole on {road} filled with water, very dangerous at night."],
        "mr": ["{road} वर मोठा खड्डा आहे, दुचाकी घसरत आहेत.", "{road} वरील बस थांब्याजवळ खड्डा आहे, कृपया दुरुस्त करा."],
        "hi": ["{road} पर बड़ा गड्ढा है, बाइक फिसल रही हैं।", "{road} पर बस स्टॉप के पास गड्ढा है, कृपया ठीक करें।"],
        "hinglish": ["{road} pe bahut bada pothole hai, bikes slip ho rahi hain.", "{road} bus stop ke paas khadda hai, jaldi theek karo."],
    },
    "drain_cover": {
        "en": ["Drain cover missing on {road}.", "Broken manhole cover on {road}, someone could fall in."],
        "mr": ["{road} वर गटाराचे झाकण नाही.", "{road} वरील गटाराचे झाकण तुटले आहे."],
        "hi": ["{road} पर नाले का ढक्कन गायब है।"],
        "hinglish": ["{road} pe gutter ka dhakkan missing hai."],
    },
    "waterlogging": {
        "en": ["Water logging on {road} after rain, road surface breaking."],
        "mr": ["पावसानंतर {road} वर पाणी साचते, रस्ता खराब होत आहे."],
        "hi": ["बारिश के बाद {road} पर पानी भर जाता है।"],
        "hinglish": ["Baarish ke baad {road} pe paani bhar jaata hai, road toot raha hai."],
    },
    "road_surface": {
        "en": ["Road surface on {road} has cracked and broken after the trench work."],
        "mr": ["खोदकामानंतर {road} चा रस्ता उखडला आहे."],
        "hi": ["खुदाई के बाद {road} की सड़क टूट गई है।"],
        "hinglish": ["Khudai ke baad {road} ki road kharab ho gayi hai."],
    },
}
TEXT_EN = {
    "pothole": ["Big pothole on {road}, two-wheelers are skidding.", "Pothole near the bus stop on {road}, please fix.",
                "Deep pothole on {road} filled with water, very dangerous at night."],
    "drain_cover": ["Drain cover missing on {road}.", "Broken drain cover on {road}."],
    "waterlogging": ["Water logging on {road} after rain, road surface breaking."],
    "road_surface": ["Road surface on {road} has broken after trench work."],
}
WT_TO_CAT = {"pothole_patch": "pothole", "surface_restoration": "road_surface",
             "trench_reinstatement": "road_surface", "drain_cover_replacement": "drain_cover"}


def complaint_text(cat, road_name):
    lang = rng.choice(["en", "mr", "hi", "hinglish"], p=[0.38, 0.27, 0.17, 0.18])
    opts = TEXTS[cat][lang]
    i = int(rng.integers(0, len(opts)))
    orig = opts[i].format(road=road_name)
    en_opts = TEXT_EN[cat]
    en = en_opts[min(i, len(en_opts) - 1)].format(road=road_name)
    return lang, orig, en


def build_complaints(wo_df, roads_df, loc_df):
    road_idx = roads_df.set_index("road_id")
    recs = []
    for _, wo in wo_df.iterrows():
        if wo.work_order_id in (GOLDEN_WO_A, GOLDEN_WO_B) or not wo.has_complaint:
            continue
        road = road_idx.loc[wo.road_id]
        cat = WT_TO_CAT[wo.work_type]
        if rng.random() < 0.06:  # category mismatch noise
            cat = rng.choice([c for c in TEXTS if c != cat])
        lang, orig, en = complaint_text(cat, road.road_name)
        created = datetime.combine(wo.issued_date - timedelta(days=int(rng.integers(0, 4))), datetime.min.time()) + timedelta(minutes=int(rng.integers(360, 1380)))
        recs.append(dict(created_at=created, ward_code=wo.ward_code, road_id=wo.road_id, locality_id=road.locality_id,
                         language=lang, text_original=orig, text_en=en, category=cat,
                         upvotes=int(rng.poisson(6 if road.road_class in ("arterial", "sub-arterial") else 3)),
                         status="CLOSED_RESOLVED", duplicate_of_key=None, linked_work_order_id=wo.work_order_id,
                         channel=rng.choice(["MyBMC app", "1916 helpline", "Ward office", "Twitter/X handle"], p=[0.55, 0.25, 0.1, 0.1]),
                         closed_at=datetime.combine(wo.completed_date, datetime.min.time()) + timedelta(hours=18)))
    # Duplicates of linked complaints
    n_base = len(recs)
    for _ in range(int(n_base * 0.22)):
        p = recs[int(rng.integers(0, n_base))]
        road = road_idx.loc[p["road_id"]]
        lang, orig, en = complaint_text(p["category"], road.road_name)
        recs.append(dict(created_at=p["created_at"] + timedelta(hours=int(rng.integers(1, 40))), ward_code=p["ward_code"],
                         road_id=p["road_id"], locality_id=p["locality_id"], language=lang, text_original=orig, text_en=en,
                         category=p["category"], upvotes=int(rng.poisson(2)), status="CLOSED_DUPLICATE",
                         duplicate_of_key=id(p), linked_work_order_id="", channel="MyBMC app", closed_at=p["closed_at"]))
    # Complaints with no work order yet
    weights = roads_df.road_class.map({"arterial": 4.0, "sub-arterial": 2.5, "collector": 1.5, "local": 1.0}).values
    weights = weights / weights.sum()
    for _ in range(620):
        road = roads_df.iloc[int(rng.choice(len(roads_df), p=weights))]
        cat = rng.choice(list(TEXTS), p=[0.62, 0.14, 0.14, 0.10])
        lang, orig, en = complaint_text(cat, road.road_name)
        created = datetime.combine(monsoon_weighted_date(START, END), datetime.min.time()) + timedelta(minutes=int(rng.integers(360, 1380)))
        recs.append(dict(created_at=created, ward_code=road.ward_code, road_id=road.road_id, locality_id=road.locality_id,
                         language=lang, text_original=orig, text_en=en, category=cat, upvotes=int(rng.poisson(4)),
                         status=rng.choice(["OPEN", "IN_PROGRESS"], p=[0.6, 0.4]), duplicate_of_key=None,
                         linked_work_order_id="", channel="MyBMC app", closed_at=None))
    # The later "pothole returned" signal on the golden road enters as a normal complaint
    golden_loc = roads_df[roads_df.road_id == GOLDEN_ROAD].iloc[0].locality_id
    recs.append(dict(created_at=datetime(2025, 8, 23, 19, 40), ward_code="M/E", road_id=GOLDEN_ROAD, locality_id=golden_loc,
                     language="hinglish",
                     text_original="Sion Trombay Road Mandala signal ke paas wahi khadda phir se khul gaya hai, abhi 2 hafte pehle hi repair hua tha.",
                     text_en="The same pothole near Mandala signal on Sion Trombay Road has opened up again; it was repaired just two weeks ago.",
                     category="pothole", upvotes=21, status="OPEN", duplicate_of_key=None, linked_work_order_id="",
                     channel="MyBMC app", closed_at=None))
    # Keep complaint IDs chronological: exactly 3,868 complaints must precede the golden pair.
    cutoff = datetime(2025, 8, 6, 8, 52)
    need = 3868 - sum(1 for r in recs if r["created_at"] < cutoff)
    if need < 0:
        removable = [i for i, r in enumerate(recs) if r["created_at"] < cutoff and r["linked_work_order_id"] == "" and r["status"] in ("OPEN", "IN_PROGRESS")]
        drop = set(removable[: -need])
        recs = [r for i, r in enumerate(recs) if i not in drop]
    for _ in range(max(0, need)):
        road = roads_df.iloc[int(rng.choice(len(roads_df), p=weights))]
        cat = rng.choice(list(TEXTS), p=[0.62, 0.14, 0.14, 0.10])
        lang, orig, en = complaint_text(cat, road.road_name)
        created = datetime.combine(monsoon_weighted_date(date(2025, 1, 1), date(2025, 8, 5)), datetime.min.time()) + timedelta(minutes=int(rng.integers(360, 1380)))
        recs.append(dict(created_at=created, ward_code=road.ward_code, road_id=road.road_id, locality_id=road.locality_id,
                         language=lang, text_original=orig, text_en=en, category=cat, upvotes=int(rng.poisson(3)),
                         status=rng.choice(["OPEN", "IN_PROGRESS", "CLOSED_NOT_ACTIONABLE"], p=[0.25, 0.15, 0.6]),
                         duplicate_of_key=None, linked_work_order_id="", channel="MyBMC app", closed_at=None))
    keys = [id(r) for r in recs]
    df = pd.DataFrame(recs)
    df["_key"] = keys
    df = df.sort_values("created_at", kind="stable").reset_index(drop=True)
    reserved = {3869, 3870}
    ids, k = [], 1
    for _ in range(len(df)):
        while k in reserved:
            k += 1
        ids.append(f"BMC25-{k:06d}")
        k += 1
    df["complaint_id"] = ids
    key_to_id = dict(zip(df._key, df.complaint_id))
    df["duplicate_of"] = df.duplicate_of_key.map(lambda x: key_to_id.get(x, "") if x else "")
    golden = pd.DataFrame([
        dict(complaint_id=GOLDEN_C_MR, created_at=datetime(2025, 8, 6, 8, 52), ward_code="M/E", road_id=GOLDEN_ROAD,
             locality_id=golden_loc, language="mr",
             text_original="सायन ट्रॉम्बे रोडवर मंडाला सिग्नलजवळ गटाराचे झाकण उघडे आहे. रात्री दिसत नाही, अपघात होऊ शकतो.",
             text_en="The drain cover near Mandala signal on Sion Trombay Road is open. It is not visible at night and could cause an accident.",
             category="pothole", upvotes=9, status="CLOSED_DUPLICATE", duplicate_of=GOLDEN_C_EN, linked_work_order_id="",
             channel="MyBMC app", closed_at=datetime(2025, 8, 9, 18, 5)),
        dict(complaint_id=GOLDEN_C_EN, created_at=datetime(2025, 8, 6, 9, 14), ward_code="M/E", road_id=GOLDEN_ROAD,
             locality_id=golden_loc, language="en",
             text_original="Huge pothole on Sion Trombay Road near Mandala signal. My scooter tyre burst this morning. Many bikes are falling here, please repair urgently.",
             text_en="Huge pothole on Sion Trombay Road near Mandala signal. My scooter tyre burst this morning. Many bikes are falling here, please repair urgently.",
             category="pothole", upvotes=37, status="CLOSED_RESOLVED", duplicate_of="", linked_work_order_id=GOLDEN_WO_A,
             channel="MyBMC app", closed_at=datetime(2025, 8, 9, 18, 0)),
    ])
    df = pd.concat([df.drop(columns=["_key", "duplicate_of_key"]), golden], ignore_index=True)
    df = df.sort_values("complaint_id").reset_index(drop=True)
    df["created_at"] = pd.to_datetime(df.created_at).dt.strftime("%Y-%m-%dT%H:%M")
    df["closed_at"] = pd.to_datetime(df.closed_at).dt.strftime("%Y-%m-%dT%H:%M").fillna("")
    cols = ["complaint_id", "created_at", "ward_code", "road_id", "locality_id", "channel", "language", "text_original",
            "text_en", "category", "upvotes", "status", "duplicate_of", "linked_work_order_id", "closed_at"]
    return df[cols]


# ---------------------------------------------------------------------------
# Accidents and social posts
# ---------------------------------------------------------------------------

def build_accidents(roads_df):
    rows = []
    w = roads_df.road_class.map({"arterial": 5.0, "sub-arterial": 2.5, "collector": 1.0, "local": 0.5}).values
    w = w / w.sum()
    for _ in range(520):
        r = roads_df.iloc[int(rng.choice(len(roads_df), p=w))]
        rows.append(dict(date=monsoon_weighted_date(START, END), road_id=r.road_id, ward_code=r.ward_code,
                         severity=rng.choice(["minor", "serious", "fatal"], p=[0.70, 0.26, 0.04]),
                         vehicle_type=rng.choice(["two-wheeler", "auto-rickshaw", "car", "BEST bus", "pedestrian"], p=[0.55, 0.15, 0.18, 0.04, 0.08]),
                         road_condition_related="Y" if rng.random() < 0.38 else "N",
                         reported_cause=None))
    golden = [
        (date(2025, 7, 28), "serious", "two-wheeler", "Y"),
        (date(2025, 8, 5), "minor", "two-wheeler", "Y"),
        (date(2025, 8, 21), "minor", "two-wheeler", "Y"),
        (date(2025, 9, 3), "serious", "auto-rickshaw", "Y"),
        (date(2025, 9, 14), "minor", "car", "N"),
    ]
    for d, s, v, rc in golden:
        rows.append(dict(date=d, road_id=GOLDEN_ROAD, ward_code="M/E", severity=s, vehicle_type=v, road_condition_related=rc, reported_cause=None))
    df = pd.DataFrame(rows).sort_values(["date", "road_id"], kind="stable").reset_index(drop=True)
    df["reported_cause"] = np.where(df.road_condition_related == "Y",
                                    rng.choice(["pothole/uneven surface", "open drain/cover", "loose gravel"], size=len(df), p=[0.75, 0.1, 0.15]),
                                    rng.choice(["speeding", "lane cutting", "poor visibility", "other"], size=len(df)))
    df.loc[(df.road_id == GOLDEN_ROAD) & (df.road_condition_related == "Y"), "reported_cause"] = "pothole/uneven surface"
    df["accident_id"] = [f"ACC25-{i + 1:04d}" for i in range(len(df))]
    df["date"] = df.date.map(d2s)
    return df[["accident_id", "date", "road_id", "ward_code", "severity", "vehicle_type", "road_condition_related", "reported_cause"]]


def build_social(complaints_df, roads_df):
    rows = []
    sample = complaints_df[complaints_df.status != "CLOSED_DUPLICATE"].sample(n=140, random_state=SEED)
    for i, (_, c) in enumerate(sample.iterrows()):
        linked = rng.random() < 0.55
        rows.append(dict(post_id=f"SP{i + 1:04d}", platform=rng.choice(["X", "Instagram", "Facebook"], p=[0.6, 0.25, 0.15]),
                         posted_at=c.created_at, language=c.language, text=c.text_original,
                         road_id=c.road_id if linked else "", linked_complaint_id=c.complaint_id if linked else "",
                         link_basis="Post quotes complaint number" if linked else "Location not verifiable",
                         likes=int(rng.poisson(25))))
    rows.append(dict(post_id=f"SP{len(rows) + 1:04d}", platform="X", posted_at="2025-08-24T08:15", language="en",
                     text="Sion Trombay Road near Mandala signal — pothole is back within two weeks of 'repair'. Ref complaint after BMC25-003870.",
                     road_id=GOLDEN_ROAD, linked_complaint_id=GOLDEN_C_EN, link_basis="Post quotes complaint number", likes=212))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data"))
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)

    wards_df, wards_geo = build_wards()
    loc_df = build_localities(wards_df)
    roads_df, roads_geo = build_roads(wards_df, loc_df)
    traffic = build_traffic(roads_df)
    facilities = build_facilities(roads_df, wards_df)
    hotspots = build_flood_hotspots(roads_df)
    rainfall = build_rainfall(wards_df)
    tides = build_tides()
    wo = build_work_orders(roads_df)
    complaints = build_complaints(wo, roads_df, loc_df)
    # Realistic categorisation noise: ~3% of complaints filed under a category their text does not describe
    # (separate RNG so the rest of the dataset is unchanged)
    nrng = np.random.default_rng(SEED + 1)
    noise_mask = (nrng.random(len(complaints)) < 0.03) & (complaints.road_id != GOLDEN_ROAD)
    cats = list(TEXTS)
    complaints.loc[noise_mask, "category"] = [nrng.choice([c for c in cats if c != cur]) for cur in complaints.loc[noise_mask, "category"]]
    link = complaints[complaints.linked_work_order_id != ""].set_index("linked_work_order_id").complaint_id
    wo["complaint_id"] = wo.work_order_id.map(link).fillna("")
    accidents = build_accidents(roads_df)
    social = build_social(complaints, roads_df)

    contractors = pd.DataFrame([dict(contractor_id=c[0], contractor_name=c[1], empanelment_class=c[2], empanelled_since=c[3]) for c in CONTRACTORS])
    rate_card = pd.DataFrame([dict(rate_card_id=r[0], work_type=r[1], repair_method=r[2], unit=r[3], standard_rate_inr=r[4], expected_life_months=r[5], effective_from="2025-04-01") for r in RATE_CARD])

    for col in ("issued_date", "completed_date", "recorded_date"):
        wo[col] = wo[col].map(d2s)
    wo_cols = ["work_order_id", "complaint_id", "road_id", "ward_code", "contractor_id", "work_type", "repair_method",
               "rate_card_id", "area_sqm", "cost_inr", "billed_to", "payment_status", "issued_date", "completed_date",
               "recorded_date", "sla_tier", "sla_days", "sla_met", "reopened_within_30d", "photo_before", "photo_after",
               "measurement_book", "engineer_certificate"]

    wards_df.to_csv(out / "wards.csv", index=False)
    loc_df.to_csv(out / "localities.csv", index=False)
    roads_df.to_csv(out / "roads.csv", index=False)
    traffic.to_csv(out / "traffic.csv", index=False)
    facilities.to_csv(out / "facilities.csv", index=False)
    hotspots.to_csv(out / "flood_hotspots.csv", index=False)
    rainfall.to_csv(out / "rainfall_daily.csv", index=False)
    tides.to_csv(out / "tides.csv", index=False)
    wo[wo_cols].to_csv(out / "work_orders.csv", index=False)
    complaints.to_csv(out / "complaints.csv", index=False)
    accidents.to_csv(out / "accidents.csv", index=False)
    social.to_csv(out / "social_posts.csv", index=False)
    contractors.to_csv(out / "contractors.csv", index=False)
    rate_card.to_csv(out / "rate_card.csv", index=False)
    (out / "roads.geojson").write_text(json.dumps(roads_geo))
    (out / "wards.geojson").write_text(json.dumps(wards_geo))
    print(f"Wrote dataset to {out}: {len(wo)} work orders, {len(complaints)} complaints, {len(roads_df)} roads")


if __name__ == "__main__":
    main()
