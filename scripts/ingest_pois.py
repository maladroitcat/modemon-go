#!/usr/bin/env python3
"""Ingest neutral OpenStreetMap POIs inside canonical Modemon GO regions."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape
from shapely.ops import unary_union

os.environ.setdefault("MPLCONFIGDIR", "/tmp/modemon-go-matplotlib")

try:
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW_POIS = DATA / "raw" / "pois"
PROCESSED = DATA / "processed"
OUTPUT = ROOT / "output"
REGIONS_PATH = PROCESSED / "regions.geojson"

FINAL_CRS = "EPSG:4326"
AREA_CRS = "EPSG:2264"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
USER_AGENT = "Modemon-GO-POI-ingestion/1.0 (educational OSM POI QA pipeline)"

EXPECTED_REGIONS = {
    "RAL-01",
    "RAL-02",
    "RAL-03A",
    "RAL-03B",
    "RAL-04",
    "RAL-05",
    "DUR-01",
    "DUR-02",
}

TARGET_KEYS = [
    "amenity",
    "shop",
    "office",
    "healthcare",
    "tourism",
    "leisure",
    "public_transport",
    "railway",
    "historic",
    "government",
    "craft",
]

PRIMARY_PRECEDENCE = [
    "healthcare",
    "amenity",
    "shop",
    "office",
    "tourism",
    "leisure",
    "public_transport",
    "railway",
    "government",
    "historic",
    "craft",
]

LOW_VALUE_VALUES = {
    "bench",
    "bicycle_parking",
    "bicycle_repair_station",
    "charging_station",
    "clock",
    "drinking_water",
    "fire_hydrant",
    "give_box",
    "grit_bin",
    "hunting_stand",
    "letter_box",
    "parking",
    "parking_entrance",
    "parking_space",
    "post_box",
    "recycling",
    "sanitary_dump_station",
    "shelter",
    "shower",
    "street_lamp",
    "telephone",
    "toilets",
    "traffic_signals",
    "vending_machine",
    "waste_basket",
    "waste_disposal",
    "water_point",
}

LOW_VALUE_KEY_VALUES = {
    ("amenity", "bench"),
    ("amenity", "bicycle_parking"),
    ("amenity", "drinking_water"),
    ("amenity", "parking"),
    ("amenity", "parking_space"),
    ("amenity", "post_box"),
    ("amenity", "recycling"),
    ("amenity", "telephone"),
    ("amenity", "toilets"),
    ("amenity", "vending_machine"),
    ("amenity", "waste_basket"),
    ("leisure", "picnic_table"),
    ("public_transport", "stop_position"),
    ("railway", "level_crossing"),
    ("railway", "signal"),
    ("railway", "switch"),
}

INHERENTLY_MEANINGFUL = {
    ("amenity", "arts_centre"),
    ("amenity", "bank"),
    ("amenity", "bar"),
    ("amenity", "biergarten"),
    ("amenity", "cafe"),
    ("amenity", "cinema"),
    ("amenity", "clinic"),
    ("amenity", "college"),
    ("amenity", "community_centre"),
    ("amenity", "conference_centre"),
    ("amenity", "courthouse"),
    ("amenity", "dentist"),
    ("amenity", "doctors"),
    ("amenity", "events_venue"),
    ("amenity", "fast_food"),
    ("amenity", "fire_station"),
    ("amenity", "food_court"),
    ("amenity", "hospital"),
    ("amenity", "library"),
    ("amenity", "marketplace"),
    ("amenity", "museum"),
    ("amenity", "pharmacy"),
    ("amenity", "place_of_worship"),
    ("amenity", "police"),
    ("amenity", "pub"),
    ("amenity", "restaurant"),
    ("amenity", "school"),
    ("amenity", "social_facility"),
    ("amenity", "theatre"),
    ("amenity", "townhall"),
    ("amenity", "university"),
    ("healthcare", "clinic"),
    ("healthcare", "doctor"),
    ("healthcare", "hospital"),
    ("healthcare", "pharmacy"),
    ("leisure", "fitness_centre"),
    ("leisure", "park"),
    ("leisure", "pitch"),
    ("leisure", "sports_centre"),
    ("public_transport", "station"),
    ("railway", "halt"),
    ("railway", "station"),
    ("shop", "department_store"),
    ("shop", "mall"),
    ("shop", "supermarket"),
    ("tourism", "attraction"),
    ("tourism", "gallery"),
    ("tourism", "hotel"),
    ("tourism", "museum"),
}

EXCLUDED_CANDIDATE_COLUMNS = [
    "region_id",
    "osm_type",
    "osm_id",
    "name",
    "primary_osm_key",
    "primary_osm_value",
    "source_geometry_type",
    "exclusion_reason",
    "raw_tags",
]


class PoiIngestionError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dirs() -> None:
    RAW_POIS.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)


def normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_regions(region_filter: str | None) -> gpd.GeoDataFrame:
    if not REGIONS_PATH.exists():
        raise PoiIngestionError(f"Cannot load canonical regions: missing {REGIONS_PATH}")
    regions = gpd.read_file(REGIONS_PATH)
    if regions.crs is None:
        raise PoiIngestionError("regions.geojson has no CRS")
    regions = regions.to_crs(FINAL_CRS)
    missing = EXPECTED_REGIONS - set(regions["region_id"])
    if missing:
        raise PoiIngestionError(f"Missing expected canonical regions: {sorted(missing)}")
    if region_filter:
        if region_filter not in EXPECTED_REGIONS:
            raise PoiIngestionError(f"Unknown region {region_filter}")
        regions = regions[regions["region_id"] == region_filter].copy()
    return regions.sort_values("region_id").reset_index(drop=True)


def polygon_components(geom: Any) -> list[Polygon]:
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    raise PoiIngestionError(f"Region geometry must be Polygon/MultiPolygon, got {geom.geom_type}")


def overpass_poly_string(poly: Polygon, max_vertices: int = 450) -> str:
    query_poly = poly
    if len(query_poly.exterior.coords) > max_vertices:
        query_poly = poly.simplify(0.00008, preserve_topology=True)
    coords = list(query_poly.exterior.coords)
    if len(coords) > max_vertices:
        step = math.ceil(len(coords) / max_vertices)
        coords = coords[::step]
        if coords[0] != coords[-1]:
            coords.append(coords[0])
    return " ".join(f"{lat:.7f} {lon:.7f}" for lon, lat in coords)


def build_overpass_query(poly: Polygon) -> str:
    poly_text = overpass_poly_string(poly)
    clauses = "\n      ".join(f'nwr["{key}"](poly:"{poly_text}");' for key in TARGET_KEYS)
    return f"""
    [out:json][timeout:120];
    (
      {clauses}
    );
    out geom;
    """


def build_region_polygon_query(geom: Any) -> str:
    clauses = []
    for component in polygon_components(geom):
        poly_text = overpass_poly_string(component)
        clauses.extend(f'nwr["{key}"](poly:"{poly_text}");' for key in TARGET_KEYS)
    body = "\n      ".join(clauses)
    return f"""
    [out:json][timeout:180];
    (
      {body}
    );
    out geom;
    """


def build_bbox_query(geom: Any) -> str:
    minx, miny, maxx, maxy = geom.bounds
    clauses = "\n      ".join(f'nwr["{key}"]({miny:.7f},{minx:.7f},{maxy:.7f},{maxx:.7f});' for key in TARGET_KEYS)
    return f"""
    [out:json][timeout:180];
    (
      {clauses}
    );
    out geom;
    """


def overpass_post(query: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(2):
        if attempt:
            time.sleep(20.0)
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    headers={"User-Agent": USER_AGENT},
                    timeout=180,
                )
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                print(f"Overpass endpoint failed ({endpoint}): {exc}", file=sys.stderr)
                time.sleep(8.0)
    raise PoiIngestionError(f"All Overpass endpoints failed: {last_error}")


def enrich_way_relation_geometry(region_id: str, elements: list[dict[str, Any]], refresh: bool) -> list[dict[str, Any]]:
    missing = [
        element
        for element in elements
        if element.get("type") in {"way", "relation"} and not element.get("geometry") and not element.get("members")
    ]
    if not missing:
        return elements
    region_dir = RAW_POIS / region_id
    enriched_by_key: dict[tuple[str, int], dict[str, Any]] = {
        (element["type"], int(element["id"])): element
        for element in elements
        if "type" in element and "id" in element
    }
    by_type: dict[str, list[int]] = {"way": [], "relation": []}
    for element in missing:
        by_type[element["type"]].append(int(element["id"]))
    chunk_index = 0
    for osm_type, ids in by_type.items():
        for start in range(0, len(ids), 100):
            chunk = ids[start : start + 100]
            if not chunk:
                continue
            chunk_index += 1
            raw_path = region_dir / f"overpass_geometry_{osm_type}_{chunk_index}.json"
            query_path = region_dir / f"overpass_geometry_{osm_type}_{chunk_index}.ql"
            query = f"""
            [out:json][timeout:120];
            {osm_type}(id:{','.join(str(v) for v in chunk)});
            out geom;
            """
            query_path.write_text(query, encoding="utf-8")
            if raw_path.exists() and not refresh:
                payload = json.loads(raw_path.read_text(encoding="utf-8"))
            else:
                payload = overpass_post(query)
                raw_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
                time.sleep(1.0)
            for element in payload.get("elements", []):
                if "type" in element and "id" in element:
                    old = enriched_by_key.get((element["type"], int(element["id"])), {})
                    merged = {**old, **element}
                    if old.get("tags") and not merged.get("tags"):
                        merged["tags"] = old["tags"]
                    enriched_by_key[(element["type"], int(element["id"]))] = merged
    enriched = list(enriched_by_key.values())
    (region_dir / "combined_elements_enriched.json").write_text(json.dumps(enriched, indent=2, sort_keys=True), encoding="utf-8")
    return enriched


def fetch_region_osm(region_id: str, geom: Any, refresh: bool) -> list[dict[str, Any]]:
    region_dir = RAW_POIS / region_id
    region_dir.mkdir(parents=True, exist_ok=True)
    combined_path = region_dir / "combined_elements.json"
    region_raw_path = region_dir / "overpass_region.json"
    region_query_path = region_dir / "overpass_region.ql"
    bbox_raw_path = region_dir / "overpass_bbox_fallback.json"
    bbox_query_path = region_dir / "overpass_bbox_fallback.ql"
    if combined_path.exists() and not refresh:
        return enrich_way_relation_geometry(region_id, json.loads(combined_path.read_text(encoding="utf-8")), refresh)
    if region_raw_path.exists() and not refresh:
        payload = json.loads(region_raw_path.read_text(encoding="utf-8"))
        elements = list({(el["type"], int(el["id"])): el for el in payload.get("elements", []) if "id" in el and "type" in el}.values())
        combined_path.write_text(json.dumps(elements, indent=2, sort_keys=True), encoding="utf-8")
        return enrich_way_relation_geometry(region_id, elements, refresh)
    query = build_region_polygon_query(geom)
    region_query_path.write_text(query, encoding="utf-8")
    try:
        payload = overpass_post(query)
        region_raw_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        elements = list({(el["type"], int(el["id"])): el for el in payload.get("elements", []) if "id" in el and "type" in el}.values())
        if not elements:
            raise PoiIngestionError("Region polygon Overpass query returned zero elements")
        combined_path.write_text(json.dumps(elements, indent=2, sort_keys=True), encoding="utf-8")
        return enrich_way_relation_geometry(region_id, elements, refresh)
    except Exception as exc:
        print(f"Region polygon Overpass query failed for {region_id}; falling back to bbox + canonical polygon filtering: {exc}", file=sys.stderr)
        query = build_bbox_query(geom)
        bbox_query_path.write_text(query, encoding="utf-8")
        payload = overpass_post(query)
        bbox_raw_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        elements = list({(el["type"], int(el["id"])): el for el in payload.get("elements", []) if "id" in el and "type" in el}.values())
        combined_path.write_text(json.dumps(elements, indent=2, sort_keys=True), encoding="utf-8")
        return enrich_way_relation_geometry(region_id, elements, refresh)

    # Legacy per-component cache path retained for older raw caches.
    all_elements: dict[tuple[str, int], dict[str, Any]] = {}
    components = polygon_components(geom)
    for idx, component in enumerate(components, start=1):
        raw_path = region_dir / f"overpass_component_{idx}.json"
        query_path = region_dir / f"overpass_component_{idx}.ql"
        query = build_overpass_query(component)
        query_path.write_text(query, encoding="utf-8")
        if raw_path.exists() and not refresh:
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
        else:
            payload = overpass_post(query)
            raw_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            time.sleep(1.0)
        for element in payload.get("elements", []):
            if "id" in element and "type" in element:
                all_elements[(element["type"], int(element["id"]))] = element
    elements = list(all_elements.values())
    (region_dir / "combined_elements.json").write_text(json.dumps(elements, indent=2, sort_keys=True), encoding="utf-8")
    return enrich_way_relation_geometry(region_id, elements, refresh)


def geometry_from_element(element: dict[str, Any]) -> Any | None:
    etype = element.get("type")
    if etype == "node":
        if "lon" in element and "lat" in element:
            return Point(float(element["lon"]), float(element["lat"]))
        center = element.get("center")
        if center:
            return Point(float(center["lon"]), float(center["lat"]))
    if etype == "way":
        coords = [(p["lon"], p["lat"]) for p in element.get("geometry", []) if "lon" in p and "lat" in p]
        if len(coords) >= 4 and coords[0] == coords[-1]:
            return Polygon(coords)
        if len(coords) >= 2:
            return LineString(coords)
    if etype == "relation":
        polygons = []
        lines = []
        for member in element.get("members", []):
            coords = [(p["lon"], p["lat"]) for p in member.get("geometry", []) if "lon" in p and "lat" in p]
            if len(coords) >= 4 and coords[0] == coords[-1] and member.get("role") in {"outer", ""}:
                polygons.append(Polygon(coords))
            elif len(coords) >= 2:
                lines.append(LineString(coords))
        if polygons:
            return unary_union(polygons)
        if lines:
            return unary_union(lines)
        center = element.get("center")
        if center:
            return Point(float(center["lon"]), float(center["lat"]))
    center = element.get("center")
    if center:
        return Point(float(center["lon"]), float(center["lat"]))
    return None


def representative_point(geom: Any) -> Point:
    if geom.geom_type == "Point":
        return geom
    if geom.geom_type in {"Polygon", "MultiPolygon"}:
        return geom.representative_point()
    return geom.interpolate(0.5, normalized=True) if hasattr(geom, "interpolate") else geom.centroid


def raw_tags_json(tags: dict[str, Any]) -> str:
    return json.dumps(tags or {}, sort_keys=True, ensure_ascii=False)


def choose_primary_category(tags: dict[str, Any]) -> tuple[str | None, str | None]:
    for key in PRIMARY_PRECEDENCE:
        value = tags.get(key)
        if value not in (None, ""):
            return key, str(value)
    return None, None


def address_from_tags(tags: dict[str, Any]) -> str:
    parts = []
    for key in sorted(k for k in tags if k.startswith("addr:")):
        parts.append(f"{key[5:]}={tags[key]}")
    return "; ".join(parts)


def has_name(tags: dict[str, Any]) -> bool:
    return any(str(tags.get(key, "")).strip() for key in ["name", "brand", "operator"])


def is_meaningful_candidate(tags: dict[str, Any], geom: Any) -> tuple[bool, str]:
    primary_key, primary_value = choose_primary_category(tags)
    if not primary_key or not primary_value:
        return False, "no_target_tag"
    value = primary_value.lower()
    if (primary_key, value) in LOW_VALUE_KEY_VALUES or value in LOW_VALUE_VALUES:
        return False, "low_value_category"
    if primary_key == "amenity" and value in {"parking", "parking_space", "bicycle_parking"}:
        return False, "parking_or_storage"
    if primary_key == "building" and value in {"yes", "residential", "house"}:
        return False, "generic_building"
    named = has_name(tags)
    if named:
        return True, "named_poi"
    if (primary_key, value) in INHERENTLY_MEANINGFUL:
        return True, "inherently_meaningful"
    if primary_key in {"shop", "office", "craft", "government"} and value not in {"yes", "no"}:
        return False, "unnamed_category_requires_review"
    if geom.geom_type in {"LineString", "MultiLineString"}:
        return False, "unnamed_line_feature"
    return False, "unnamed_not_inherently_meaningful"


def make_poi_id(region_id: str, osm_type: str, osm_id: Any) -> str:
    return f"{region_id}_osm_{osm_type}_{osm_id}"


def element_to_record(
    element: dict[str, Any],
    region: pd.Series,
    retrieved_at: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    tags = element.get("tags", {}) or {}
    geom = geometry_from_element(element)
    osm_type = element.get("type")
    osm_id = element.get("id")
    primary_key, primary_value = choose_primary_category(tags)
    base_excluded = {
        "region_id": region["region_id"],
        "osm_type": osm_type,
        "osm_id": osm_id,
        "name": tags.get("name") or tags.get("brand") or tags.get("operator"),
        "primary_osm_key": primary_key,
        "primary_osm_value": primary_value,
        "source_geometry_type": None if geom is None else geom.geom_type,
        "raw_tags": raw_tags_json(tags),
    }
    if osm_type is None or osm_id is None:
        return None, {**base_excluded, "exclusion_reason": "missing_osm_identity"}
    if geom is None or geom.is_empty:
        return None, {**base_excluded, "exclusion_reason": "missing_geometry"}
    if not geom.is_valid:
        geom = geom.buffer(0)
    rep = representative_point(geom)
    if not region.geometry.covers(rep):
        return None, {**base_excluded, "exclusion_reason": "representative_point_outside_region"}
    keep, reason = is_meaningful_candidate(tags, geom)
    if not keep:
        return None, {**base_excluded, "exclusion_reason": reason}
    name = tags.get("name") or tags.get("brand") or tags.get("operator")
    record = {
        "poi_id": make_poi_id(region["region_id"], osm_type, osm_id),
        "region_id": region["region_id"],
        "parent_city": region["parent_city"],
        "osm_type": osm_type,
        "osm_id": int(osm_id),
        "name": name,
        "normalized_name": normalize_name(name),
        "source_geometry_type": geom.geom_type,
        "representative_latitude": rep.y,
        "representative_longitude": rep.x,
        "primary_osm_key": primary_key,
        "primary_osm_value": primary_value,
        "brand": tags.get("brand"),
        "operator": tags.get("operator"),
        "address": address_from_tags(tags),
        "wikidata": tags.get("wikidata"),
        "wikipedia": tags.get("wikipedia"),
        "website": tags.get("website") or tags.get("contact:website"),
        "raw_tags": raw_tags_json(tags),
        "retrieved_at_utc": retrieved_at,
        "source": "OpenStreetMap Overpass API",
        "review_required": False,
        "geometry": geom,
    }
    return record, {**base_excluded, "exclusion_reason": f"retained:{reason}"}


def ingest_regions(regions: gpd.GeoDataFrame, refresh: bool, allow_partial: bool) -> tuple[gpd.GeoDataFrame, pd.DataFrame, pd.DataFrame]:
    retained: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    qa_rows: list[dict[str, Any]] = []
    retrieved_at = utc_now()
    for _, region in regions.iterrows():
        region_id = region["region_id"]
        try:
            elements = fetch_region_osm(region_id, region.geometry, refresh)
        except Exception as exc:
            if not allow_partial:
                raise
            print(f"FAILED {region_id}: {exc}", file=sys.stderr)
            qa_rows.append({"region_id": region_id, "retrieval_failure": str(exc)})
            continue
        candidate_count = len(elements)
        retained_before = len(retained)
        excluded_before = len(excluded)
        for element in elements:
            record, audit = element_to_record(element, region, retrieved_at)
            if record:
                retained.append(record)
            excluded.append(audit)
        region_retained = retained[retained_before:]
        region_excluded = excluded[excluded_before:]
        named = sum(1 for item in region_retained if item.get("name"))
        geom_counts = pd.Series([item["source_geometry_type"] for item in region_retained]).value_counts().to_dict() if region_retained else {}
        categories = pd.Series(
            [f"{item['primary_osm_key']}={item['primary_osm_value']}" for item in region_retained]
        ).value_counts()
        qa_rows.append(
            {
                "region_id": region_id,
                "parent_city": region["parent_city"],
                "total_candidate_osm_features": candidate_count,
                "total_retained_pois": len(region_retained),
                "total_excluded": len([x for x in region_excluded if not str(x.get("exclusion_reason", "")).startswith("retained:")]),
                "percent_with_names": round((named / len(region_retained) * 100), 2) if region_retained else 0.0,
                "geometry_type_counts": json.dumps(geom_counts, sort_keys=True),
                "top_20_categories": json.dumps(categories.head(20).to_dict(), sort_keys=True),
            }
        )
        if region_id in {"RAL-01", "RAL-03A", "RAL-04", "RAL-05", "DUR-01", "DUR-02"} and not region_retained:
            print(f"WARNING: major region {region_id} retained zero POIs", file=sys.stderr)
    if retained:
        poi_gdf = gpd.GeoDataFrame(retained, geometry="geometry", crs=FINAL_CRS)
    else:
        poi_gdf = gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=FINAL_CRS)
    excluded_df = pd.DataFrame(excluded)
    qa_df = pd.DataFrame(qa_rows)
    return poi_gdf, excluded_df, qa_df


def validate_pois(pois: gpd.GeoDataFrame, regions: gpd.GeoDataFrame) -> None:
    if pois.empty:
        raise PoiIngestionError("No POIs retained")
    if pois.crs is None or pois.crs.to_string() != FINAL_CRS:
        raise PoiIngestionError("POI output CRS is not EPSG:4326")
    if pois["poi_id"].duplicated().any():
        dupes = pois.loc[pois["poi_id"].duplicated(), "poi_id"].tolist()
        raise PoiIngestionError(f"Duplicate poi_id values: {dupes[:10]}")
    if pois["osm_type"].isna().any() or pois["osm_id"].isna().any():
        raise PoiIngestionError("osm_type or osm_id is missing")
    if not pois["representative_latitude"].between(-90, 90).all():
        raise PoiIngestionError("Representative latitude outside WGS84 range")
    if not pois["representative_longitude"].between(-180, 180).all():
        raise PoiIngestionError("Representative longitude outside WGS84 range")
    for raw_tags in pois["raw_tags"]:
        json.loads(raw_tags)
    region_lookup = regions.set_index("region_id").geometry.to_dict()
    for row in pois.itertuples():
        point = Point(row.representative_longitude, row.representative_latitude)
        if not region_lookup[row.region_id].covers(point):
            raise PoiIngestionError(f"POI {row.poi_id} representative point is outside {row.region_id}")


def possible_duplicates(pois: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    if pois.empty:
        return pd.DataFrame(columns=["poi_id_a", "poi_id_b", "normalized_name", "distance_feet", "reason"])
    projected = pois.to_crs(AREA_CRS).copy()
    projected["rep_geometry"] = gpd.points_from_xy(projected["representative_longitude"], projected["representative_latitude"], crs=FINAL_CRS).to_crs(AREA_CRS)
    grouped = projected[projected["normalized_name"].fillna("") != ""].groupby("normalized_name")
    for normalized_name, group in grouped:
        records = list(group.itertuples())
        if len(records) < 2:
            continue
        for i, a in enumerate(records):
            for b in records[i + 1 :]:
                distance = a.rep_geometry.distance(b.rep_geometry)
                same_brand = bool(a.brand) and a.brand == b.brand
                same_operator = bool(a.operator) and a.operator == b.operator
                same_address = bool(a.address) and a.address == b.address
                if distance <= 100 or same_brand or same_operator or same_address:
                    rows.append(
                        {
                            "poi_id_a": a.poi_id,
                            "poi_id_b": b.poi_id,
                            "region_id_a": a.region_id,
                            "region_id_b": b.region_id,
                            "normalized_name": normalized_name,
                            "distance_feet": round(distance, 1),
                            "same_brand": same_brand,
                            "same_operator": same_operator,
                            "same_address": same_address,
                            "reason": "same normalized name with proximity/brand/operator/address signal",
                        }
                    )
    return pd.DataFrame(rows)


def write_outputs(pois: gpd.GeoDataFrame, excluded: pd.DataFrame, qa: pd.DataFrame, regions: gpd.GeoDataFrame) -> dict[str, Any]:
    validate_pois(pois, regions)
    pois = pois.sort_values(["region_id", "poi_id"]).reset_index(drop=True)
    pois.to_file(PROCESSED / "pois.geojson", driver="GeoJSON")
    csv_df = pd.DataFrame(pois.drop(columns="geometry"))
    csv_df["geometry_wkt"] = pois.geometry.to_wkt()
    csv_df.to_csv(PROCESSED / "pois.csv", index=False)

    counts = (
        pois.assign(has_name=pois["name"].fillna("").astype(str).str.strip() != "")
        .groupby(["region_id", "parent_city"], as_index=False)
        .agg(total_pois=("poi_id", "count"), named_pois=("has_name", "sum"))
    )
    counts["unnamed_meaningful_pois"] = counts["total_pois"] - counts["named_pois"]
    counts.to_csv(PROCESSED / "poi_counts_by_region.csv", index=False)

    category_counts = (
        pois.groupby(["region_id", "primary_osm_key", "primary_osm_value"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["region_id", "count"], ascending=[True, False])
    )
    category_counts.to_csv(PROCESSED / "poi_counts_by_osm_category.csv", index=False)

    dupes = possible_duplicates(pois)
    dupes.to_csv(PROCESSED / "possible_duplicate_pois.csv", index=False)

    excluded_out = excluded.copy()
    for col in EXCLUDED_CANDIDATE_COLUMNS:
        if col not in excluded_out.columns:
            excluded_out[col] = None
    excluded_out[EXCLUDED_CANDIDATE_COLUMNS].to_csv(PROCESSED / "excluded_poi_candidates.csv", index=False)
    qa["possible_duplicate_count"] = qa["region_id"].map(
        lambda rid: int(((dupes.get("region_id_a") == rid) | (dupes.get("region_id_b") == rid)).sum()) if not dupes.empty else 0
    )
    qa.to_csv(PROCESSED / "poi_ingestion_report.csv", index=False)
    make_maps(pois, regions)
    write_readme()
    return {
        "counts": counts,
        "category_counts": category_counts,
        "duplicates": dupes,
        "excluded": excluded_out,
        "qa": qa,
    }


def make_maps(pois: gpd.GeoDataFrame, regions: gpd.GeoDataFrame) -> None:
    if plt is None:
        print("matplotlib unavailable; skipping POI validation maps")
        return
    for city, filename in [("Raleigh", "poi_validation_raleigh.png"), ("Durham", "poi_validation_durham.png")]:
        city_regions = regions[regions["parent_city"] == city]
        if city_regions.empty:
            continue
        city_pois = pois[pois["parent_city"] == city]
        fig, ax = plt.subplots(figsize=(12, 10))
        city_regions.boundary.plot(ax=ax, color="#222222", linewidth=1.8)
        reps = gpd.GeoDataFrame(
            city_pois.drop(columns="geometry"),
            geometry=gpd.points_from_xy(city_pois["representative_longitude"], city_pois["representative_latitude"]),
            crs=FINAL_CRS,
        )
        if not reps.empty:
            reps.plot(ax=ax, markersize=9, color="#d62728", alpha=0.65)
        for _, row in city_regions.iterrows():
            pt = row.geometry.representative_point()
            ax.text(pt.x, pt.y, row["region_id"], fontsize=10, weight="bold", ha="center", va="center")
        ax.set_title(f"{city} POI Validation")
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(OUTPUT / filename, dpi=180)
        plt.close(fig)


def write_readme() -> None:
    text = """# Modemon GO POI Data

This pipeline extracts neutral OpenStreetMap points of interest inside the eight canonical Modemon GO gameplay regions.

OSM source categories are not Modemon gameplay habitats. Habitat labels are derived separately in the next stage.

## POI Definition

A POI is a named or categorically meaningful OSM feature representing a place a player could plausibly encounter or associate with human activity. The pipeline targets commercial, civic, institutional, healthcare, entertainment, educational, recreation, transit, tourism, office, government, historic, and craft features.

## Included Tag Families

The Overpass query requests objects with at least one of: `amenity`, `shop`, `office`, `healthcare`, `tourism`, `leisure`, `public_transport`, `railway`, `historic`, `government`, or `craft`.

## Exclusion Logic

Filtering is centralized in `is_meaningful_candidate()`. Named POIs are generally retained unless they are low-value infrastructure. Unnamed features are retained only when their source category is inherently meaningful, such as hospitals, pharmacies, schools, libraries, museums, transit stations, and similar places. Low-value objects such as benches, trash cans, post boxes, toilets, recycling points, generic parking, street lamps, utility-like railway features, and unnamed line features are excluded.

## Spatial Assignment

Each candidate keeps its original OSM geometry when practical. A representative point is calculated for deterministic indexing. A candidate is assigned to a region only when that representative point is covered by the canonical region polygon. This avoids duplicating one POI across neighboring gameplay containers.

## Primary Category Precedence

`primary_osm_key` and `primary_osm_value` are neutral source-data categories, not habitats. Precedence is: healthcare, amenity, shop, office, tourism, leisure, public_transport, railway, government, historic, craft.

## Deduplication

POIs are never merged solely because names match. Primary identity is deterministic by region plus OSM type and ID: `REGION_osm_TYPE_ID`. `possible_duplicate_pois.csv` reports likely real-world duplicates using normalized name, proximity, brand/operator, and address signals for manual review.

## Outputs

- `data/processed/pois.geojson`: retained POIs with source geometry
- `data/processed/pois.csv`: flat inspection table with representative coordinates and raw tags as JSON text
- `data/processed/poi_counts_by_region.csv`: count summary by gameplay region
- `data/processed/poi_counts_by_osm_category.csv`: source category counts by region
- `data/processed/possible_duplicate_pois.csv`: likely duplicate candidates, not merged
- `data/processed/excluded_poi_candidates.csv`: excluded candidate audit sample/source table
- `data/processed/poi_ingestion_report.csv`: QA report by region
- `output/poi_validation_raleigh.png` and `output/poi_validation_durham.png`: region boundaries and retained representative points

## Source And Attribution

Data source: OpenStreetMap via Overpass API. OpenStreetMap data is available under the Open Database License (ODbL) and requires OpenStreetMap attribution. Raw Overpass responses are cached by region under `data/raw/pois/`.

## Known Limitations

OpenStreetMap completeness varies by area. Some real-world places may be missing, duplicated, represented only as buildings, or represented by both a point and polygon. This stage intentionally avoids habitat labeling, rarity assignment, spawn logic, and Modemon model-family decisions.
"""
    (DATA / "POI_README.md").write_text(text, encoding="utf-8")


def print_summary(outputs: dict[str, Any]) -> None:
    counts = outputs["counts"]
    category_counts = outputs["category_counts"]
    duplicates = outputs["duplicates"]
    excluded = outputs["excluded"]
    pois = pd.read_csv(PROCESSED / "pois.csv")
    print("\nPOI count per region:")
    print(counts.to_string(index=False))
    print("\nTop OSM categories per region:")
    for region_id, group in category_counts.groupby("region_id"):
        print(f"\n{region_id}")
        print(group.head(10).to_string(index=False))
    print("\nSample of 20 retained POIs:")
    print(pois[["poi_id", "region_id", "name", "primary_osm_key", "primary_osm_value"]].head(20).to_string(index=False))
    print("\nSample of 20 excluded candidates:")
    sample_excluded = excluded[~excluded["exclusion_reason"].astype(str).str.startswith("retained:")]
    print(sample_excluded[["region_id", "osm_type", "osm_id", "name", "primary_osm_key", "primary_osm_value", "exclusion_reason"]].head(20).to_string(index=False))
    print("\n20 most common excluded categories:")
    if not sample_excluded.empty:
        cat = (sample_excluded["primary_osm_key"].fillna("none") + "=" + sample_excluded["primary_osm_value"].fillna("none")).value_counts().head(20)
        print(cat.to_string())
    print(f"\nLikely duplicate count: {len(duplicates)}")
    print("\nValidation maps:")
    print(f"- {OUTPUT / 'poi_validation_raleigh.png'}")
    print(f"- {OUTPUT / 'poi_validation_durham.png'}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", help="Run one canonical region ID")
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached raw Overpass responses")
    args = parser.parse_args()
    ensure_dirs()
    regions = load_regions(args.region)
    pois, excluded, qa = ingest_regions(regions, args.refresh, args.allow_partial)
    outputs = write_outputs(pois, excluded, qa, regions)
    print_summary(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
