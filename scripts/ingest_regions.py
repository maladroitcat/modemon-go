#!/usr/bin/env python3
"""Fetch Modemon GO region polygons from authoritative GIS/OSM sources."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
from shapely import force_2d, make_valid
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

try:
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

try:
    import contextily as cx
except Exception:  # pragma: no cover
    cx = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUTPUT = ROOT / "output"
RALEIGH_RAW = RAW / "raleigh"
DURHAM_RAW = RAW / "durham"
NCSU_RAW = RAW / "ncsu"

FINAL_CRS = "EPSG:4326"
AREA_CRS = "EPSG:2264"
USER_AGENT = "Modemon-GO-region-ingestion/1.0 (educational reproducible GIS pipeline)"

RALEIGH_ORG = "v400IkDOw1ad7Yad"
RALEIGH_BASE = f"https://services.arcgis.com/{RALEIGH_ORG}/arcgis/rest/services"
RALEIGH_DOWNTOWN = f"{RALEIGH_BASE}/Municipal_Service_Districts/FeatureServer/0/query"
RALEIGH_PARKS = f"{RALEIGH_BASE}/Developed_Parks/FeatureServer/0/query"
DURHAM_PLACE_TYPE = "https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Planning/MapServer/25/query"

NCSU_GDRIVE_ID = "1tq2hbWdxTGEzkuqyJlljgjR44uDZ7ZR4"
NCSU_ZIP_NAME = "CAMPUSPERIMETER_ALL.zip"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = "https://overpass-api.de/api/interpreter"


class IngestionError(RuntimeError):
    pass


@dataclass
class RegionSpec:
    region_id: str
    parent_city: str
    display_name: str
    geometry_source: str
    source_authority: str
    source_query_or_filter: str
    review_required: bool
    notes: str = ""


def ensure_dirs() -> None:
    for path in [RALEIGH_RAW, DURHAM_RAW, NCSU_RAW, PROCESSED, OUTPUT]:
        path.mkdir(parents=True, exist_ok=True)


def retrieved_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def requests_get(url: str, *, params: dict[str, Any] | None = None, timeout: int = 90) -> requests.Response:
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response


def arcgis_query(url: str, params: dict[str, Any], raw_path: Path) -> gpd.GeoDataFrame:
    merged = {
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        **params,
    }
    response = requests_get(url, params=merged)
    payload = response.json()
    write_json(raw_path, payload)
    if "error" in payload:
        raise IngestionError(f"ArcGIS query failed for {url}: {payload['error']}")
    gdf = gpd.read_file(raw_path)
    if gdf.empty:
        raise IngestionError(f"ArcGIS query returned no features: {url} {merged}")
    if gdf.crs is None:
        gdf = gdf.set_crs(FINAL_CRS)
    return gdf


def dissolve_geometries(gdf: gpd.GeoDataFrame) -> Any:
    if gdf.empty:
        raise IngestionError("Cannot dissolve an empty GeoDataFrame")
    return unary_union([geom for geom in gdf.geometry if geom is not None and not geom.is_empty])


def only_polygons(geom: Any) -> Any:
    if geom is None or geom.is_empty:
        raise IngestionError("Geometry is empty")
    if geom.geom_type in {"Polygon", "MultiPolygon"}:
        return geom
    if geom.geom_type == "GeometryCollection":
        polys = [part for part in geom.geoms if part.geom_type in {"Polygon", "MultiPolygon"}]
        if polys:
            return unary_union(polys)
    raise IngestionError(f"Required Polygon/MultiPolygon, got {geom.geom_type}")


def normalize_geometry(geom: Any, region_id: str) -> tuple[Any, bool]:
    geom = force_2d(geom)
    geom = only_polygons(geom)
    if not geom.is_valid:
        geom = make_valid(geom)
        geom = only_polygons(geom)
    if not geom.is_valid:
        raise IngestionError(f"{region_id} remains invalid after make_valid")
    if geom.geom_type == "Polygon":
        return geom, True
    if geom.geom_type == "MultiPolygon":
        return geom, True
    raise IngestionError(f"{region_id} normalized to unsupported geometry type {geom.geom_type}")


def feature(region: RegionSpec, geom: Any, original_crs: str | None, retrieved: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    geom, valid = normalize_geometry(geom, region.region_id)
    props = {
        "region_id": region.region_id,
        "parent_city": region.parent_city,
        "display_name": region.display_name,
        "geometry_source": region.geometry_source,
        "source_authority": region.source_authority,
        "source_query_or_filter": region.source_query_or_filter,
        "retrieved_at_utc": retrieved,
        "original_crs": original_crs or "unknown",
        "final_crs": FINAL_CRS,
        "review_required": region.review_required,
        "geometry_valid": valid,
        "notes": region.notes,
    }
    if extra:
        props.update(extra)
    return {"type": "Feature", "properties": props, "geometry": geom.__geo_interface__}


def gdf_feature_collection(features: list[dict[str, Any]]) -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame.from_features(features, crs=FINAL_CRS)
    if gdf.crs is None or gdf.crs.to_string() != FINAL_CRS:
        raise IngestionError("Final CRS is not EPSG:4326")
    bad = sorted(set(gdf.geometry.geom_type) - {"Polygon", "MultiPolygon"})
    if bad:
        raise IngestionError(f"Unsupported final geometry types: {bad}")
    invalid = gdf[~gdf.geometry.is_valid]
    if not invalid.empty:
        raise IngestionError(f"Invalid final geometries: {invalid['region_id'].tolist()}")
    return gdf


def fetch_raleigh_downtown() -> dict[str, Any]:
    retrieved = retrieved_at()
    gdf = arcgis_query(
        RALEIGH_DOWNTOWN,
        {"where": "Name='Downtown'"},
        RALEIGH_RAW / "ral_01_downtown_municipal_service_district.geojson",
    )
    names = sorted(str(v) for v in gdf.get("Name", pd.Series(dtype=str)).dropna().unique())
    print(f"RAL-01 Municipal_Service_Districts matched names: {names}")
    if names != ["Downtown"]:
        raise IngestionError(f"RAL-01 did not uniquely return Name='Downtown': {names}")
    return feature(
        RegionSpec(
            "RAL-01",
            "Raleigh",
            "Downtown Raleigh",
            "City of Raleigh Municipal_Service_Districts",
            "City of Raleigh",
            "Name = 'Downtown'",
            False,
            "Downtown municipal service district, not police district or older downtown boundary.",
        ),
        dissolve_geometries(gdf.to_crs(FINAL_CRS)),
        str(gdf.crs),
        retrieved,
    )


def fetch_raleigh_parks() -> list[dict[str, Any]]:
    retrieved = retrieved_at()
    all_matches: dict[str, list[str]] = {}
    selected = []
    specs = [
        ("RAL-02", "Dorothea Dix Park", "Dix", "Dix Park"),
        ("RAL-03B", "Pullen Park", "Pullen", "Pullen"),
    ]
    for region_id, display, needle, expected_name in specs:
        gdf = arcgis_query(
            RALEIGH_PARKS,
            {"where": f"UPPER(NAME) LIKE UPPER('%{needle}%')"},
            RALEIGH_RAW / f"{region_id.lower()}_developed_parks_{needle.lower()}.geojson",
        )
        names = sorted(str(v) for v in gdf["NAME"].dropna().unique())
        all_matches[needle] = names
        print(f"Developed_Parks NAME matches for '{needle}': {names}")
        chosen_names = [name for name in names if name.casefold() == expected_name.casefold()]
        if len(chosen_names) != 1:
            raise IngestionError(f"{region_id} ambiguous park selection for {display}: {chosen_names}")
        chosen = gdf[gdf["NAME"] == chosen_names[0]].to_crs(FINAL_CRS)
        selected.append(
            feature(
                RegionSpec(
                    region_id,
                    "Raleigh",
                    display,
                    "City of Raleigh Developed_Parks",
                    "City of Raleigh",
                    f"NAME contains '{needle}', selected NAME = '{chosen_names[0]}'",
                    False,
                    "Dissolved all polygons for selected park name without convex hull or simplification.",
                ),
                dissolve_geometries(chosen),
                str(gdf.crs),
                retrieved,
                {"source_matched_names": "; ".join(names)},
            )
        )
    return selected


def download_ncsu_zip() -> Path:
    zip_path = NCSU_RAW / NCSU_ZIP_NAME
    if zip_path.exists() and zip_path.stat().st_size > 0:
        return zip_path
    try:
        import gdown

        print(f"Downloading NC State Campus Perimeters with gdown: {NCSU_GDRIVE_ID}")
        gdown.download(id=NCSU_GDRIVE_ID, output=str(zip_path), quiet=False, fuzzy=False)
        if zip_path.exists() and zip_path.stat().st_size > 0:
            return zip_path
    except Exception as exc:
        print(f"gdown unavailable or failed ({exc}); trying direct Google Drive download")

    session = requests.Session()
    url = "https://drive.google.com/uc"
    response = session.get(url, params={"export": "download", "id": NCSU_GDRIVE_ID}, headers={"User-Agent": USER_AGENT}, timeout=120)
    token = None
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            token = value
            break
    if token:
        response = session.get(
            url,
            params={"export": "download", "confirm": token, "id": NCSU_GDRIVE_ID},
            headers={"User-Agent": USER_AGENT},
            timeout=120,
        )
    response.raise_for_status()
    zip_path.write_bytes(response.content)
    if zip_path.stat().st_size == 0:
        raise IngestionError("NC State Campus Perimeters ZIP download is empty")
    return zip_path


def fetch_ncsu_campuses() -> list[dict[str, Any]]:
    retrieved = retrieved_at()
    zip_path = download_ncsu_zip()
    extract_dir = NCSU_RAW / "campus_perimeters"
    extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    shp_files = sorted(extract_dir.rglob("*.shp"))
    if not shp_files:
        raise IngestionError(f"No shapefile found in {zip_path}")
    shp = shp_files[0]
    gdf = gpd.read_file(shp)
    print(f"NC State Campus Perimeters shapefile: {shp}")
    print(f"NC State columns: {list(gdf.columns)}")
    categorical_report: dict[str, list[str]] = {}
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        unique = sorted(str(v) for v in gdf[col].dropna().unique())
        if 0 < len(unique) <= 40:
            categorical_report[col] = unique
            print(f"NC State unique {col}: {unique}")
    write_json(NCSU_RAW / "campus_perimeters_columns_and_unique_values.json", categorical_report)
    original_crs = str(gdf.crs)
    if gdf.crs is None:
        raise IngestionError("NC State shapefile has no CRS")

    precinct_col = choose_ncsu_precinct_column(gdf)
    out = []
    for region_id, display, expected in [
        ("RAL-03A", "NC State Central Campus", "Central"),
        ("RAL-04", "NC State Centennial Campus", "Centennial"),
    ]:
        matches = gdf[gdf[precinct_col].astype(str).str.fullmatch(expected, case=False, na=False)]
        if matches.empty:
            matches = gdf[gdf[precinct_col].astype(str).str.contains(expected, case=False, na=False)]
        values = sorted(str(v) for v in matches[precinct_col].dropna().unique())
        if len(values) != 1:
            raise IngestionError(f"{region_id} cannot be uniquely identified in {precinct_col}: {values}")
        matches = matches.to_crs(FINAL_CRS)
        out.append(
            feature(
                RegionSpec(
                    region_id,
                    "Raleigh",
                    display,
                    "NC State Facilities Campus Perimeters shapefile",
                    "NC State Facilities",
                    f"{precinct_col} = '{values[0]}'",
                    False,
                    "Official NC State campus perimeter precinct record dissolved if multipart.",
                ),
                dissolve_geometries(matches),
                original_crs,
                retrieved,
                {"ncsu_precinct_name": values[0]},
            )
        )
    return out


def choose_ncsu_precinct_column(gdf: gpd.GeoDataFrame) -> str:
    candidates = []
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        values = [str(v) for v in gdf[col].dropna().unique()]
        has_central = any(re.search(r"\bCentral\b", value, re.I) for value in values)
        has_centennial = any(re.search(r"\bCentennial\b", value, re.I) for value in values)
        if has_central and has_centennial:
            candidates.append(col)
    if len(candidates) != 1:
        raise IngestionError(f"Could not uniquely identify NC State precinct column: {candidates}")
    return candidates[0]


def fetch_durham_downtown() -> dict[str, Any]:
    retrieved = retrieved_at()
    gdf = arcgis_query(
        DURHAM_PLACE_TYPE,
        {"where": "PlaceType='DT'"},
        DURHAM_RAW / "dur_01_place_type_dt.geojson",
    )
    values = sorted(str(v) for v in gdf.get("PlaceType", pd.Series(dtype=str)).dropna().unique())
    print(f"DUR-01 PlaceType matches: {values}")
    if values != ["DT"]:
        raise IngestionError(f"DUR-01 did not uniquely return PlaceType='DT': {values}")
    return feature(
        RegionSpec(
            "DUR-01",
            "Durham",
            "Downtown Durham",
            "City/County of Durham PublicServices/Planning Place Type",
            "City/County of Durham GIS",
            "PlaceType = 'DT'",
            False,
            "Dissolved Downtown Place Type polygons; not Bullpen social district.",
        ),
        dissolve_geometries(gdf.to_crs(FINAL_CRS)),
        str(gdf.crs),
        retrieved,
    )


def nominatim_polygon(
    query: str,
    raw_path: Path,
    extra_params: dict[str, Any] | None = None,
) -> tuple[Any | None, dict[str, Any] | None, list[dict[str, Any]]]:
    params = {
        "q": query,
        "format": "jsonv2",
        "polygon_geojson": 1,
        "limit": 10,
    }
    if extra_params:
        params.update(extra_params)
    response = requests_get(NOMINATIM, params=params)
    payload = response.json()
    write_json(raw_path, payload)
    polygonal = []
    for item in payload:
        geo = item.get("geojson")
        if not geo:
            continue
        geom_type = geo.get("type")
        print(f"Nominatim candidate for '{query}': {item.get('display_name')} [{geom_type}] osm={item.get('osm_type')}/{item.get('osm_id')}")
        if geom_type in {"Polygon", "MultiPolygon"}:
            polygonal.append(item)
    if len(polygonal) == 1:
        return shape(polygonal[0]["geojson"]), polygonal[0], payload
    if len(polygonal) > 1:
        exact = [p for p in polygonal if query.split(",")[0].lower() in p.get("display_name", "").lower()]
        if len(exact) == 1:
            return shape(exact[0]["geojson"]), exact[0], payload
        raise IngestionError(f"Ambiguous Nominatim polygon candidates for {query}: {[p.get('display_name') for p in polygonal]}")
    return None, None, payload


def print_osm_candidate(prefix: str, osm_type: Any, osm_id: Any, tags: dict[str, Any], geom: Any) -> None:
    area_acres = gpd.GeoSeries([geom], crs=FINAL_CRS).to_crs(AREA_CRS).area.iloc[0] / 43560
    print(f"{prefix} OSM type: {osm_type}")
    print(f"{prefix} OSM ID: {osm_id}")
    print(f"{prefix} name: {tags.get('name')}")
    print(f"{prefix} tags: {json.dumps(tags, sort_keys=True)}")
    print(f"{prefix} geometry type: {geom.geom_type}")
    print(f"{prefix} area acres: {area_acres:.3f}")


def overpass_polygons(query: str, lat: float, lon: float, raw_path: Path, radius_m: int = 2000) -> list[tuple[Any, dict[str, Any]]]:
    name = query.split(",")[0]
    escaped = "|".join(re.escape(v) for v in osm_name_variants(name))
    q = f"""
    [out:json][timeout:90];
    (
      nwr(around:{radius_m},{lat},{lon})["name"~"{escaped}",i];
      nwr(around:{radius_m},{lat},{lon})["alt_name"~"{escaped}",i];
      nwr(around:{radius_m},{lat},{lon})["operator"~"{escaped}",i];
      nwr(around:{radius_m},{lat},{lon})["brand"~"{escaped}",i];
    );
    out geom tags;
    """
    response = requests.post(OVERPASS, data={"data": q}, headers={"User-Agent": USER_AGENT}, timeout=120)
    response.raise_for_status()
    payload = response.json()
    write_json(raw_path, payload)
    candidates: list[tuple[Any, dict[str, Any]]] = []
    for el in payload.get("elements", []):
        geom = element_to_polygon(el)
        if geom is None:
            continue
        tags = el.get("tags", {})
        if is_defensible_osm_polygon(tags, name):
            candidates.append((geom, el))
            print(f"Overpass polygon candidate for '{name}': {tags.get('name')} type={el.get('type')} id={el.get('id')}")
    return candidates


def overpass_duke_university(raw_path: Path) -> list[tuple[Any, dict[str, Any]]]:
    q = """
    [out:json][timeout:90];
    (
      nwr["name"="Duke University"]["amenity"="university"];
      nwr["name"="Duke University"]["landuse"="education"];
      nwr["name"="Duke University"]["place"~"university|campus",i];
    );
    out geom tags;
    """
    response = requests.post(OVERPASS, data={"data": q}, headers={"User-Agent": USER_AGENT}, timeout=120)
    response.raise_for_status()
    payload = response.json()
    write_json(raw_path, payload)
    candidates = []
    for el in payload.get("elements", []):
        geom = element_to_polygon(el)
        if geom is None:
            continue
        tags = el.get("tags", {})
        if is_duke_university_area(tags):
            candidates.append((geom, el))
            print_osm_candidate("DUR-02 Overpass candidate", el.get("type"), el.get("id"), tags, geom)
    return candidates


def element_to_polygon(el: dict[str, Any]) -> Any | None:
    if el.get("type") == "way" and "geometry" in el:
        coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
        if len(coords) >= 4 and coords[0] == coords[-1]:
            poly = Polygon(coords)
            return make_valid(poly) if not poly.is_valid else poly
    if el.get("type") == "relation":
        outers = []
        for member in el.get("members", []):
            if member.get("role") in {"outer", ""} and "geometry" in member:
                coords = [(p["lon"], p["lat"]) for p in member["geometry"]]
                if len(coords) >= 4 and coords[0] == coords[-1]:
                    outers.append(Polygon(coords))
        if outers:
            return unary_union(outers)
    return None


def osm_name_variants(search_name: str) -> list[str]:
    variants = [search_name]
    stripped = re.sub(r"^Duke University\s+", "", search_name, flags=re.I).strip()
    if stripped and stripped.casefold() != search_name.casefold():
        variants.append(stripped)
    stripped = re.sub(r"^Duke\s+", "", search_name, flags=re.I).strip()
    if stripped and all(stripped.casefold() != v.casefold() for v in variants):
        variants.append(stripped)
    return variants


def is_defensible_osm_polygon(tags: dict[str, Any], search_name: str) -> bool:
    haystack = " ".join(str(tags.get(k, "")) for k in ["name", "alt_name", "operator", "brand"]).lower()
    reject = ["chiller", "hotel", "inn", "suite", "parking", "garage", "garden"]
    if any(word in haystack for word in reject):
        return False
    name_match = False
    for variant in osm_name_variants(search_name):
        words = [w for w in re.split(r"\W+", variant.lower()) if len(w) > 2]
        if words and all(w in haystack for w in words):
            name_match = True
            break
    if not name_match:
        return False
    campus_like_keys = [
        tags.get("amenity") in {"university", "hospital", "clinic"},
        tags.get("healthcare") in {"hospital", "clinic"},
        tags.get("landuse") in {"education", "institutional", "commercial"},
        tags.get("building") in {"hospital", "university", "yes"},
        tags.get("type") == "multipolygon",
    ]
    return any(campus_like_keys)


def is_duke_university_area(tags: dict[str, Any]) -> bool:
    name = str(tags.get("name", ""))
    haystack = " ".join(str(tags.get(k, "")) for k in ["name", "alt_name", "operator", "brand"]).lower()
    reject = [
        "building",
        "chiller",
        "clinic",
        "facility",
        "garden",
        "garage",
        "hospital",
        "hotel",
        "inn",
        "medical",
        "office",
        "parking",
        "plant",
        "school of",
        "suite",
    ]
    if name.casefold() != "duke university":
        return False
    if any(word in haystack for word in reject):
        return False
    return (
        tags.get("amenity") == "university"
        or tags.get("landuse") == "education"
        or str(tags.get("place", "")).lower() in {"university", "campus"}
    )


def geocode_point(query: str, raw_path: Path) -> tuple[float, float] | None:
    response = requests_get(NOMINATIM, params={"q": query, "format": "jsonv2", "limit": 1})
    payload = response.json()
    write_json(raw_path, payload)
    if not payload:
        return None
    return float(payload[0]["lat"]), float(payload[0]["lon"])


def fetch_osm_named_region(region: RegionSpec, raw_dir: Path, allow_overpass: bool = True) -> dict[str, Any]:
    retrieved = retrieved_at()
    query = region.source_query_or_filter
    geom, item, payload = nominatim_polygon(query, raw_dir / f"{region.region_id.lower()}_nominatim.json")
    if geom is not None:
        extra = {
            "osm_display_name": item.get("display_name"),
            "osm_type": item.get("osm_type"),
            "osm_id": item.get("osm_id"),
            "notes": f"{region.notes} Nominatim returned Polygon/MultiPolygon.",
        }
        return feature(region, geom, FINAL_CRS, retrieved, extra)
    point_types = [p.get("geojson", {}).get("type") for p in payload if p.get("geojson")]
    print(f"Nominatim did not return an acceptable polygon for {region.region_id}; geometry types found: {point_types}")
    if not allow_overpass:
        raise IngestionError(f"{region.region_id} OSM lookup only returned non-polygon geometry")
    point = geocode_point(query, raw_dir / f"{region.region_id.lower()}_geocode_point_for_overpass.json")
    if point is None and "duke" in query.lower():
        point = geocode_point(
            "Duke University, Durham, North Carolina",
            raw_dir / f"{region.region_id.lower()}_duke_university_geocode_point_for_overpass.json",
        )
    if point is None:
        raise IngestionError(f"{region.region_id} could not be geocoded for Overpass fallback")
    candidates = overpass_polygons(query, point[0], point[1], raw_dir / f"{region.region_id.lower()}_overpass.json")
    if len(candidates) != 1:
        raise IngestionError(f"{region.region_id} Overpass returned {len(candidates)} defensible polygon candidates; refusing ambiguous selection")
    geom, el = candidates[0]
    extra = {
        "osm_type": el.get("type"),
        "osm_id": el.get("id"),
        "osm_tags_name": el.get("tags", {}).get("name"),
        "notes": f"{region.notes} Overpass polygon selected after Nominatim returned no polygon.",
    }
    return feature(region, geom, FINAL_CRS, retrieved, extra)


def fetch_wakemed() -> dict[str, Any]:
    spec = RegionSpec(
        "RAL-05",
        "Raleigh",
        "WakeMed Raleigh Campus",
        "OpenStreetMap polygon fallback",
        "OpenStreetMap",
        "WakeMed Raleigh Campus, Raleigh, North Carolina",
        True,
        "OSM fallback; no authoritative public campus-perimeter layer identified.",
    )
    try:
        return fetch_osm_named_region(spec, RALEIGH_RAW, allow_overpass=True)
    except IngestionError as first_error:
        print(f"WakeMed named-campus OSM lookup failed: {first_error}")
    retrieved = retrieved_at()
    point = geocode_point("3000 New Bern Avenue, Raleigh, North Carolina", RALEIGH_RAW / "ral_05_3000_new_bern_geocode.json")
    if point is None:
        raise IngestionError("RAL-05 could not geocode 3000 New Bern Avenue for Overpass fallback")
    candidates = overpass_polygons(
        "WakeMed",
        point[0],
        point[1],
        RALEIGH_RAW / "ral_05_wakemed_overpass_new_bern.json",
        radius_m=1600,
    )
    hospital = []
    for geom, el in candidates:
        tags = el.get("tags", {})
        if "wakemed" in " ".join(str(tags.get(k, "")) for k in ["name", "operator", "brand"]).lower():
            if tags.get("amenity") == "hospital" or tags.get("healthcare") == "hospital" or "hospital" in str(tags.get("name", "")).lower():
                hospital.append((geom, el))
    if not hospital:
        raise IngestionError("RAL-05 no defensible polygonal WakeMed hospital campus candidate found")
    if len(hospital) > 1:
        unioned = unary_union([geom for geom, _ in hospital])
        ids = "; ".join(f"{el.get('type')}/{el.get('id')}:{el.get('tags', {}).get('name')}" for _, el in hospital)
    else:
        unioned, el = hospital[0]
        ids = f"{el.get('type')}/{el.get('id')}:{el.get('tags', {}).get('name')}"
    return feature(
        RegionSpec(
            "RAL-05",
            "Raleigh",
            "WakeMed Raleigh Campus",
            "OpenStreetMap polygon fallback",
            "OpenStreetMap",
            "Overpass near 3000 New Bern Avenue; name/operator/brand contains WakeMed and hospital/healthcare tags",
            True,
            "OSM fallback union of clearly associated polygonal WakeMed hospital features.",
        ),
        unioned,
        FINAL_CRS,
        retrieved,
        {"osm_selected_features": ids},
    )


def fetch_duke_university() -> dict[str, Any]:
    retrieved = retrieved_at()
    query = "Duke University, Durham, North Carolina"
    geom, item, payload = nominatim_polygon(
        query,
        DURHAM_RAW / "dur-02_duke_university_nominatim.json",
        {"addressdetails": 1, "namedetails": 1},
    )
    accepted_item = None
    if geom is not None and item is not None:
        tags = {
            "name": item.get("name"),
            "category": item.get("category"),
            "type": item.get("type"),
            "osm_type": item.get("osm_type"),
            "osm_id": item.get("osm_id"),
            "display_name": item.get("display_name"),
        }
        if item.get("namedetails"):
            tags.update({f"namedetails:{k}": v for k, v in item["namedetails"].items()})
        if item.get("category") == "amenity" and item.get("type") == "university" and is_duke_university_area({"name": item.get("name"), "amenity": "university"}):
            accepted_item = item
            print_osm_candidate("DUR-02 Nominatim accepted candidate", item.get("osm_type"), item.get("osm_id"), tags, geom)
        else:
            print(f"DUR-02 rejected Nominatim polygon candidate: {tags}")
    else:
        for candidate in payload:
            geo_type = candidate.get("geojson", {}).get("type")
            print(
                "DUR-02 Nominatim candidate:",
                candidate.get("osm_type"),
                candidate.get("osm_id"),
                candidate.get("name"),
                candidate.get("category"),
                candidate.get("type"),
                geo_type,
            )

    if accepted_item is None:
        candidates = overpass_duke_university(DURHAM_RAW / "dur-02_duke_university_overpass.json")
        if len(candidates) != 1:
            raise IngestionError(f"DUR-02 Overpass returned {len(candidates)} defensible Duke University area candidates")
        geom, el = candidates[0]
        accepted_item = {
            "osm_type": el.get("type"),
            "osm_id": el.get("id"),
            "name": el.get("tags", {}).get("name"),
            "display_name": el.get("tags", {}).get("name"),
        }

    return feature(
        RegionSpec(
            "DUR-02",
            "Durham",
            "Duke University",
            "OpenStreetMap",
            "OpenStreetMap",
            query,
            True,
            "Broad physical gameplay container. Internal Duke campus, healthcare, research, and other gameplay subregions will be derived later.",
        ),
        geom,
        FINAL_CRS,
        retrieved,
        {
            "osm_type": accepted_item.get("osm_type"),
            "osm_id": accepted_item.get("osm_id"),
            "osm_name": accepted_item.get("name"),
            "osm_display_name": accepted_item.get("display_name"),
        },
    )


def add_area_columns(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    area_gdf = gdf.to_crs(AREA_CRS)
    df = gdf.drop(columns="geometry").copy()
    sqft = area_gdf.geometry.area
    df["area_acres"] = (sqft / 43560).round(3)
    df["area_sq_miles"] = (sqft / 27878400).round(4)
    df["geometry_type"] = gdf.geometry.geom_type
    return df


def save_outputs(features: list[dict[str, Any]]) -> pd.DataFrame:
    if len(features) != 8:
        raise IngestionError(f"Expected 8 child features, got {len(features)}")
    gdf = gdf_feature_collection(features)
    gdf = gdf.sort_values("region_id")
    raleigh = gdf[gdf["parent_city"] == "Raleigh"]
    durham = gdf[gdf["parent_city"] == "Durham"]
    raleigh.to_file(PROCESSED / "raleigh_regions.geojson", driver="GeoJSON")
    durham.to_file(PROCESSED / "durham_regions.geojson", driver="GeoJSON")
    gdf.to_file(PROCESSED / "regions.geojson", driver="GeoJSON")

    city_features = []
    for city, sub in [("Raleigh", raleigh), ("Durham", durham)]:
        unioned, valid = normalize_geometry(unary_union(list(sub.geometry)), city)
        city_features.append(
            {
                "type": "Feature",
                "properties": {
                    "parent_city": city,
                    "display_name": city,
                    "geometry_source": "Unary union of Modemon GO child regions",
                    "source_authority": "Derived gameplay container",
                    "source_query_or_filter": "unary_union(child geometries)",
                    "retrieved_at_utc": retrieved_at(),
                    "original_crs": FINAL_CRS,
                    "final_crs": FINAL_CRS,
                    "review_required": bool(sub["review_required"].any()),
                    "geometry_valid": valid,
                    "notes": "Derived from child polygons without filling gaps or connecting disconnected areas.",
                },
                "geometry": unioned.__geo_interface__,
            }
        )
    city_gdf = gdf_feature_collection(city_features)
    if len(city_gdf) != 2:
        raise IngestionError("city_game_areas.geojson must contain exactly two features")
    city_gdf.to_file(PROCESSED / "city_game_areas.geojson", driver="GeoJSON")

    summary = add_area_columns(gdf)
    cols = [
        "region_id",
        "parent_city",
        "display_name",
        "geometry_type",
        "area_acres",
        "area_sq_miles",
        "geometry_source",
        "source_authority",
        "review_required",
        "geometry_valid",
        "source_query_or_filter",
        "retrieved_at_utc",
        "notes",
    ]
    summary[cols].to_csv(PROCESSED / "regions_summary.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    return summary[cols]


def plot_validation(gdf: gpd.GeoDataFrame, path: Path, title: str) -> None:
    if plt is None:
        print("matplotlib is unavailable; skipping validation plots")
        return
    plot_gdf = gdf.to_crs(3857)
    fig, ax = plt.subplots(figsize=(12, 10))
    colors = {"Raleigh": "#1f77b4", "Durham": "#d62728"}
    for city, sub in plot_gdf.groupby("parent_city"):
        sub.boundary.plot(ax=ax, linewidth=2.2, color=colors.get(city, "black"), label=city)
        sub.plot(ax=ax, facecolor="none", edgecolor=colors.get(city, "black"), linewidth=1.2)
        for _, row in sub.iterrows():
            pt = row.geometry.representative_point()
            ax.text(pt.x, pt.y, row["region_id"], fontsize=9, weight="bold", ha="center", va="center")
    if cx is not None:
        try:
            cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, attribution_size=7)
        except Exception as exc:
            print(f"contextily basemap unavailable for {path.name}: {exc}")
    ax.set_title(title)
    ax.set_axis_off()
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_plots() -> None:
    gdf = gpd.read_file(PROCESSED / "regions.geojson")
    plot_validation(gdf, OUTPUT / "region_validation_map.png", "Modemon GO Region Validation")
    plot_validation(gdf[gdf["parent_city"] == "Raleigh"], OUTPUT / "raleigh_validation.png", "Raleigh Region Validation")
    plot_validation(gdf[gdf["parent_city"] == "Durham"], OUTPUT / "durham_validation.png", "Durham Region Validation")


def make_partial_plots(gdf: gpd.GeoDataFrame) -> None:
    plot_validation(gdf, OUTPUT / "region_validation_map.png", "Modemon GO Region Validation (Partial)")
    raleigh = gdf[gdf["parent_city"] == "Raleigh"]
    durham = gdf[gdf["parent_city"] == "Durham"]
    if not raleigh.empty:
        plot_validation(raleigh, OUTPUT / "raleigh_validation.png", "Raleigh Region Validation (Partial)")
    if not durham.empty:
        plot_validation(durham, OUTPUT / "durham_validation.png", "Durham Region Validation (Partial)")


def write_readme(summary: pd.DataFrame, failures: list[str]) -> None:
    if failures:
        outputs = [
            "- `processed/regions_partial.geojson`: successfully retrieved child regions only",
            "- `processed/regions_summary_partial.csv`: QA area calculations for successfully retrieved regions in EPSG:2264",
            "- `output/region_validation_map.png`: visual QA map for successfully retrieved regions",
            "- `output/raleigh_validation.png` and/or `output/durham_validation.png`: city-specific visual QA maps where data was retrieved",
        ]
    else:
        outputs = [
            "- `processed/raleigh_regions.geojson`: Raleigh child regions",
            "- `processed/durham_regions.geojson`: Durham child regions",
            "- `processed/regions.geojson`: all 8 child regions",
            "- `processed/city_game_areas.geojson`: Raleigh and Durham parent gameplay areas, derived by unary-unioning child polygons without filling gaps",
            "- `processed/regions_summary.csv`: QA area calculations in EPSG:2264",
            "- `output/region_validation_map.png`, `output/raleigh_validation.png`, `output/durham_validation.png`: visual QA maps",
        ]
    lines = [
        "# Modemon GO Region Data",
        "",
        f"Retrieval date: {retrieved_at()}",
        "",
        "These GeoJSON files are Modemon GO gameplay containers. They are not represented as legal municipal, property, university, or medical-campus boundaries unless the underlying authoritative dataset explicitly defines them that way.",
        "",
        "Top-level regions are broad physical gameplay containers. They are not intended to encode all meaningful neighborhoods, campus divisions, or Modémon habitats. Internal gameplay regions are derived separately.",
        "",
        "## Outputs",
        "",
        *outputs,
        "",
        "## Region Sources",
        "",
    ]
    if not summary.empty:
        for _, row in summary.sort_values("region_id").iterrows():
            review = "yes" if row["review_required"] else "no"
            authority = "OSM fallback" if row["source_authority"] == "OpenStreetMap" else "authoritative source"
            lines.extend(
                [
                    f"### {row['region_id']} - {row['display_name']}",
                    "",
                    f"- Represents: {row['display_name']} gameplay container beneath {row['parent_city']}",
                    f"- Source: {row['geometry_source']}",
                    f"- Authority class: {authority}",
                    f"- Query/filter: `{row['source_query_or_filter']}`",
                    f"- Retrieved: {row['retrieved_at_utc']}",
                    f"- Review required: {review}",
                    f"- Notes: {row['notes']}",
                    "",
                ]
            )
    if failures:
        lines.extend(["## Failed Or Ambiguous Retrievals", ""])
        lines.extend(f"- {failure}" for failure in failures)
        lines.append("")
    lines.extend(
        [
            "## Licensing And Attribution",
            "",
            "- City of Raleigh, City/County of Durham, and NC State source data should be attributed according to their public GIS/open-data terms.",
            "- OpenStreetMap fallback geometries require OpenStreetMap attribution and are subject to the Open Database License (ODbL).",
            "- This pipeline preserves raw downloaded responses under `data/raw/` for auditability.",
            "",
        ]
    )
    (DATA / "README.md").write_text("\n".join(lines), encoding="utf-8")


def run(allow_partial: bool) -> tuple[pd.DataFrame, list[str]]:
    ensure_dirs()
    failures: list[str] = []
    features: list[dict[str, Any]] = []
    tasks = [
        ("RAL-01", lambda: [fetch_raleigh_downtown()]),
        ("RAL-02/RAL-03B", fetch_raleigh_parks),
        ("RAL-03A/RAL-04", fetch_ncsu_campuses),
        ("RAL-05", lambda: [fetch_wakemed()]),
        ("DUR-01", lambda: [fetch_durham_downtown()]),
        ("DUR-02", lambda: [fetch_duke_university()]),
    ]
    for label, fn in tasks:
        try:
            features.extend(fn())
        except Exception as exc:
            message = f"{label}: {exc}"
            failures.append(message)
            print(f"FAILED {message}", file=sys.stderr)
            if not allow_partial:
                write_readme(pd.DataFrame(), failures)
                raise

    if failures and allow_partial:
        partial_path = PROCESSED / "regions_partial.geojson"
        if features:
            partial_gdf = gdf_feature_collection(features).sort_values("region_id")
            partial_gdf.to_file(partial_path, driver="GeoJSON")
            summary = add_area_columns(partial_gdf)
            summary.to_csv(PROCESSED / "regions_summary_partial.csv", index=False)
            make_partial_plots(partial_gdf)
        else:
            summary = pd.DataFrame()
        write_readme(summary, failures)
        return summary, failures

    summary = save_outputs(features)
    make_plots()
    write_readme(summary, failures)
    return summary, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial", action="store_true", help="Write partial diagnostics instead of aborting on first failed source.")
    args = parser.parse_args()
    summary, failures = run(args.allow_partial)
    if not summary.empty:
        print("\nFinal/partial region summary:")
        print(summary[["region_id", "display_name", "geometry_type", "area_acres", "area_sq_miles", "source_authority", "review_required"]].to_string(index=False))
    if failures:
        print("\nFailed or ambiguous extractions:")
        for failure in failures:
            print(f"- {failure}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
