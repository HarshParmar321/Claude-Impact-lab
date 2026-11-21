"""Loads the dataset once and keeps the derived (deterministic) tables in memory."""

from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from app.config import DATA_DIR
from app.calculations import audit as audit_calc
from app.calculations import budget as budget_calc

STR_COLS = {"complaint_id", "linked_work_order_id", "duplicate_of", "road_id", "nearest_road_id", "linked_complaint_id", "ward_code"}


def _read(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / f"{name}.csv", keep_default_na=False, na_values=[])
    for c in df.columns:
        if c in STR_COLS:
            df[c] = df[c].astype(str)
    return df


class DataStore:
    def __init__(self) -> None:
        self.complaints = _read("complaints")
        self.work_orders = _read("work_orders")
        self.rate_card = _read("rate_card")
        self.roads = _read("roads")
        self.contractors = _read("contractors")
        self.wards = _read("wards")
        self.traffic = _read("traffic")
        self.accidents = _read("accidents")
        self.flood_hotspots = _read("flood_hotspots")
        self.rainfall = _read("rainfall_daily")
        self.tides = _read("tides")
        self.facilities = _read("facilities")
        self.localities = _read("localities")
        self.social_posts = _read("social_posts")
        self.roads_geojson = json.loads((DATA_DIR / "roads.geojson").read_text())
        self.wards_geojson = json.loads((DATA_DIR / "wards.geojson").read_text())

        for c in ("area_sqm",):
            self.work_orders[c] = pd.to_numeric(self.work_orders[c])
        self.work_orders["cost_inr"] = pd.to_numeric(self.work_orders.cost_inr).astype(int)

        audit, dups = audit_calc.build_audit_table(self.work_orders, self.roads, self.rate_card)
        roads_idx = self.roads.set_index("road_id")
        audit["road_name"] = audit.road_id.map(roads_idx.road_name)
        audit["road_under_dlp"] = audit.road_id.map(roads_idx.under_dlp)
        audit["road_class"] = audit.road_id.map(roads_idx.road_class)
        audit["contractor_name"] = audit.contractor_id.map(self.contractors.set_index("contractor_id").contractor_name)
        self.audit = audit
        self.duplicates = dups
        self.audit_idx = audit.set_index("work_order_id", drop=False)
        self.priority = budget_calc.priority_scores(self.roads, self.traffic, self.accidents, self.flood_hotspots,
                                                    self.rainfall, self.tides, self.facilities, self.complaints, audit)
        self.durability = budget_calc.method_durability(audit, self.rate_card)

    # convenience lookups -------------------------------------------------
    def road(self, road_id: str) -> dict:
        return self.roads.set_index("road_id").loc[road_id].to_dict() | {"road_id": road_id}

    def work_order(self, wo_id: str) -> dict | None:
        if wo_id not in self.audit_idx.index:
            return None
        return self.audit_idx.loc[wo_id].to_dict()

    def complaint(self, cid: str) -> dict | None:
        m = self.complaints[self.complaints.complaint_id == cid]
        return None if m.empty else m.iloc[0].to_dict()


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return DataStore()
