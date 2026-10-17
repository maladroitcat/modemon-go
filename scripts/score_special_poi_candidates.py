#!/usr/bin/env python3
"""Rank existing POIs for human review as possible future special destinations."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from matplotlib.lines import Line2D
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUTPUT = ROOT / "output"
CONFIG = ROOT / "data/config/special_poi_candidate_config.yaml"
SCORE_FIELDS = ["specialization_score", "habitat_distinctiveness_score",
                "discovery_value_score", "accessibility_score"]


def normalized(value):
    if value is None or (not isinstance(value, (dict, list)) and pd.isna(value)):
        return ""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", str(value)).casefold()))


def flag(value):
    return normalized(value) in {"true", "1", "yes"}


def raw_tags(value):
    if isinstance(value, dict):
        tags = value
    else:
        try:
            tags = json.loads(value)
        except json.JSONDecodeError:
            # The canonical labeled CSV contains Python dictionary text from GeoPandas.
            tags = ast.literal_eval(value)
    if not isinstance(tags, dict):
        raise ValueError("raw_tags must contain an OSM dictionary")
    return {str(k): str(v) for k, v in tags.items()}


def matches(rule, tags):
    def condition(c):
        value = tags.get(c["key"], "")
        if "values" in c:
            return value in [str(v) for v in c["values"]]
        if "tokens" in c:
            return bool(set(value.split(";")) & set(c["tokens"]))
        return bool(value and normalized(value) not in {"no", "false", "0", "none"}) if c.get("exists") else False
    return (not rule.get("any") or any(condition(c) for c in rule["any"])) and all(
        condition(c) for c in rule.get("all", []))


def meaningful_name(value, config):
    name = normalized(value)
    return bool(name and name not in set(config["names"]["generic_names"])
                and not any(re.search(pattern, name) for pattern in config["names"]["generic_patterns"]))


def input_hashes():
    paths = [p for p in DATA.iterdir() if p.is_file() and not p.name.startswith("special_poi_")]
    paths += [p for p in (ROOT / "data/raw").rglob("*") if p.is_file() and p.name != ".DS_Store"]
    paths += list((ROOT / "data/config").glob("*.yaml"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def load_inputs(config):
    pois = gpd.read_file(DATA / "pois_labeled.geojson")
    table = pd.read_csv(DATA / "pois_labeled.csv", keep_default_na=False)
    regions = gpd.read_file(DATA / "regions.geojson")
    zones = gpd.read_file(DATA / "habitat_zones.geojson")
    neutral = gpd.read_file(DATA / "habitat_unclassified_areas.geojson")
    if len(pois) != config["expected_poi_count"] or len(table) != len(pois):
        raise ValueError("Unexpected canonical POI count")
    if pois.poi_id.isna().any() or pois.poi_id.duplicated().any() or table.poi_id.duplicated().any():
        raise ValueError("POI IDs must be present and unique")
    if set(pois.poi_id) != set(table.poi_id):
        raise ValueError("POI CSV and GeoJSON inventories disagree")
    joined = table.set_index("poi_id").loc[pois.poi_id]
    for field in ["region_id", "parent_city", "name", "habitat_primary", "habitat_secondary"]:
        if pois[field].fillna("").astype(str).tolist() != joined[field].fillna("").astype(str).tolist():
            raise ValueError(f"POI CSV and GeoJSON disagree: {field}")
    if [raw_tags(v) for v in pois.raw_tags] != [raw_tags(v) for v in joined.raw_tags]:
        raise ValueError("POI raw tags disagree between source formats")
    if set(regions.region_id) != set(config["canonical_region_ids"]) or regions.region_id.duplicated().any():
        raise ValueError("Expected eight canonical regions")
    for frame in [pois, regions, zones, neutral]:
        if frame.crs is None:
            raise ValueError("Canonical inputs must declare their CRS")
    for frame in [regions, zones, neutral]:
        if frame.geometry.is_empty.any() or not frame.geometry.is_valid.all():
            raise ValueError("Invalid canonical context geometry")
    if set(zones.habitat_primary) - set(config["habitats"]) or not set(zones.region_id) <= set(regions.region_id):
        raise ValueError("Invalid canonical habitat-zone metadata")
    return pois.to_crs(4326), regions.to_crs(4326), zones.to_crs(4326), neutral.to_crs(4326)


def build_context(pois, regions, zones, neutral, config):
    counts = pois.assign(habitat_primary=pois.habitat_primary.fillna(""))
    totals = counts.groupby("region_id").size().to_dict()
    frequencies = counts.groupby(["region_id", "habitat_primary"]).size().to_dict()
    pairs = counts.assign(habitat_secondary=counts.habitat_secondary.fillna("")).groupby(
        ["region_id", "habitat_primary", "habitat_secondary"]).size().to_dict()
    projected = zones.to_crs(config["analysis_crs"])
    zone_areas = projected.assign(weight=projected.geometry.area).groupby(["region_id", "habitat_primary"]).weight.sum().to_dict()
    area_totals = projected.assign(weight=projected.geometry.area).groupby("region_id").weight.sum().to_dict()
    return {"totals": totals, "frequencies": frequencies, "pairs": pairs,
            "zone_areas": zone_areas, "area_totals": area_totals,
            "names": Counter(normalized(v) for v in pois.name),
            "regions": regions.set_index("region_id"), "zones": zones, "neutral": neutral}


def score_poi(row, context, config):
    tags = raw_tags(row.raw_tags)
    name = meaningful_name(row.get("name"), config)
    primary, secondary = row.get("habitat_primary") or "", row.get("habitat_secondary") or ""
    primary = "" if pd.isna(primary) else primary
    secondary = "" if pd.isna(secondary) else secondary
    rid = row.region_id
    specialization_matches = [r for r in config["specialization"]["rules"] if matches(r, tags)]
    strongest = sorted(specialization_matches, key=lambda r: (-r["points"], r["id"]))
    rule = strongest[0] if strongest else {"id": "SP_DEFAULT", "points": config["specialization"]["default_points"], "reason": "Generic or insufficiently specific source function"}
    specialization = float(rule["points"])
    access = next((r for r in config["accessibility"]["rules"] if matches(r, tags)), None)
    if access is None:
        a = config["accessibility"]
        access = {"id": "AC_UNKNOWN", "status": a["default_status"], "points": a["default_points"], "reason": a["default_reason"]}

    total = context["totals"].get(rid, 0)
    primary_frequency = context["frequencies"].get((rid, primary), 0)
    primary_share = primary_frequency / total if total else 0
    area_total = context["area_totals"].get(rid, 0)
    area_share = context["zone_areas"].get((rid, primary), 0) / area_total if area_total else None
    secondary_share = context["frequencies"].get((rid, secondary), 0) / total if total else 0
    pair_share = context["pairs"].get((rid, primary, secondary), 0) / total if total else 0
    valid_primary = primary in config["habitats"]
    dc = config["distinctiveness"]
    distinct_parts = {
        "primary_poi_rarity": dc["primary_poi_rarity_points"] * (1-primary_share) if valid_primary else 0,
        "primary_zone_rarity": (dc["primary_zone_rarity_points"] * (1-area_share) if area_share is not None else dc["unavailable_zone_context_points"]) if valid_primary else 0,
        "secondary_context": dc["secondary_context_points"] * (1-secondary_share) if secondary in config["habitats"] else 0,
    }
    dv = config["discovery"]
    discovery_parts = {
        "meaningful_name": dv["meaningful_name_points"] if name else 0,
        "name_frequency": (dv["unique_name_points"] if context["names"][normalized(row.get("name"))] == 1 else dv["repeated_name_points"]) if name else 0,
        "non_generic_function": dv["non_generic_function_points"] if specialization >= dv["non_generic_function_min_specialization"] else 0,
        "wikidata": dv["wikidata_points"] if tags.get("wikidata") else 0,
        "wikipedia": dv["wikipedia_points"] if any(v for k,v in tags.items() if k == "wikipedia" or k.startswith("wikipedia:")) else 0,
        "alternate_pair": dv["alternate_pair_points"] * (1-pair_share) if valid_primary and secondary in config["habitats"] else 0,
        "tagged_brand_penalty": -dv["tagged_brand_penalty"] if tags.get("brand") or tags.get("brand:wikidata") else 0,
    }
    bounds = config["dimension_bounds"]
    values = [specialization, sum(distinct_parts.values()), sum(discovery_parts.values()), float(access["points"])]
    bounded = [round(max(0, min(value, bounds[key])), 4) for key,value in zip(bounds, values)]
    scores = dict(zip(SCORE_FIELDS, bounded))
    raw_score = round(sum(bounded), 4)
    exclusions = []
    if not primary:
        exclusions.append("missing_primary_habitat")
    elif not valid_primary:
        exclusions.append("invalid_primary_habitat")
    if not name:
        exclusions.append("missing_meaningful_name")
    geometry = row.geometry
    if geometry is None or geometry.is_empty or not geometry.is_valid:
        exclusions.append("invalid_geometry")
    valid_region = rid in context["regions"].index
    if not valid_region:
        exclusions.append("invalid_parent_region")
    lon, lat = row.get("representative_longitude"), row.get("representative_latitude")
    point = None
    try:
        lon, lat = float(lon), float(lat)
        if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("Invalid representative coordinates")
        point = Point(lon, lat)
    except (ValueError, TypeError):
        exclusions.append("invalid_representative_coordinates")
    if valid_region and point is not None and not context["regions"].loc[rid].geometry.covers(point):
        exclusions.append("representative_point_outside_parent")
    habitat_review = flag(row.get("habitat_review_required", False))
    if habitat_review:
        exclusions.append("habitat_classification_requires_review")
    if access["status"] == "restricted_or_inappropriate":
        exclusions.append("restricted_or_inappropriate")
    review_reasons = []
    if access["status"] != "likely_public":
        review_reasons.append(access["status"])
    if habitat_review:
        review_reasons.append("habitat_classification_requires_review")
    if not valid_primary:
        review_reasons.append("no_defensible_primary_habitat")
    if row.primary_osm_value in config["review"]["ambiguous_values"]:
        review_reasons.append("ambiguous_source_function")
    if tags.get("fixme"):
        review_reasons.append("source_fixme")
    if area_share is None:
        review_reasons.append("missing_zone_area_context")
    zone_ids, neutral_ids = [], []
    if valid_region and point is not None:
        for key, destination in [("zones", zone_ids), ("neutral", neutral_ids)]:
            frame = context[key]
            part = frame[frame.region_id == rid]
            destination.extend(sorted(part.loc[part.geometry.covers(point), "zone_id"]))
    rationale = {
        "specialization": {"rule": rule["id"], "reason": rule["reason"], "all_matching_rules": [r["id"] for r in strongest]},
        "distinctiveness": distinct_parts, "discovery": discovery_parts,
        "accessibility": {"rule": access["id"], "reason": access["reason"]},
    }
    return {**scores, "raw_candidate_score": raw_score,
            "candidate_access_status": access["status"], "candidate_access_reason": access["reason"],
            "candidate_eligible": not exclusions, "candidate_exclusion_reason": ";".join(exclusions),
            "candidate_review_required": bool(review_reasons), "candidate_review_reasons": ";".join(review_reasons),
            "specialization_rule_id": rule["id"], "specialization_reason": rule["reason"],
            "accessibility_rule_id": access["id"], "scoring_rationale": json.dumps(rationale, sort_keys=True),
            "region_total_pois": total, "region_primary_habitat_pois": primary_frequency,
            "region_primary_habitat_poi_share": primary_share, "region_primary_habitat_zone_area_share": area_share,
            "region_secondary_habitat_primary_poi_share": secondary_share,
            "context_zone_ids": json.dumps(zone_ids), "context_neutral_area_ids": json.dumps(neutral_ids),
            "config_version": config["version"]}


def score_all(pois, context, config):
    rows = []
    for _, row in pois.sort_values("poi_id").iterrows():
        output = row.drop(labels=["geometry"]).to_dict()
        output["raw_tags"] = json.dumps(raw_tags(row.raw_tags), sort_keys=True)
        output.update(score_poi(row, context, config))
        rows.append(output)
    return pd.DataFrame(rows)


def shortlist_candidates(scores, regions, config):
    settings = config["shortlist"]
    eligible = scores[scores.candidate_eligible & (scores.raw_candidate_score >= settings["minimum_raw_score"])
                      & (scores.specialization_score >= settings["minimum_specialization_score"])].copy()
    projected_regions = regions.to_crs(config["analysis_crs"]).set_index("region_id")
    unit_meters = projected_regions.crs.axis_info[0].unit_conversion_factor
    points = gpd.GeoSeries([Point(float(row.representative_longitude), float(row.representative_latitude))
                           for row in eligible.itertuples()], index=eligible.poi_id, crs=4326).to_crs(config["analysis_crs"])
    result = []
    for rid, group in eligible.groupby("region_id", sort=True):
        region_geom = projected_regions.loc[rid].geometry
        x0,y0,x1,y1 = region_geom.bounds
        small_region = (region_geom.area / 43560 < settings["small_region_max_area_acres"]
                        or math.hypot(x1-x0, y1-y0) * unit_meters <= settings["small_region_max_span_meters"])
        selected, subtype_counts, seen_names, seen_entities, seen_habitats = [], Counter(), set(), set(), set()
        remaining = group.to_dict("records")
        while remaining and len(selected) < settings["max_per_region"]:
            candidates = []
            for row in remaining:
                subtype = (row["primary_osm_key"], row["primary_osm_value"])
                entity = raw_tags(row["raw_tags"]).get("wikidata", "")
                if (subtype_counts[subtype] >= settings["maximum_same_subtype"]
                        or normalized(row["name"]) in seen_names or (entity and entity in seen_entities)):
                    continue
                nearest = min((points[row["poi_id"]].distance(points[s["poi_id"]]) * unit_meters for s in selected), default=float("inf"))
                novelty = row["habitat_primary"] not in seen_habitats
                utility = row["raw_candidate_score"] + (settings["new_habitat_priority_bonus"] if novelty else 0)
                candidates.append((row, nearest, novelty, utility))
            spaced = [c for c in candidates if c[1] >= settings["preferred_spacing_meters"]]
            if not spaced and small_region:
                spaced = [c for c in candidates if c[1] >= settings["relaxed_spacing_meters"]]
            if not spaced:
                break
            row, nearest, novelty, utility = sorted(spaced, key=lambda c: (-c[3], -c[0]["raw_candidate_score"], c[0]["poi_id"]))[0]
            row = {**row, "region_candidate_rank": len(selected)+1,
                   "selection_priority_score": utility, "new_habitat_at_selection": novelty,
                   "spacing_relaxation_available": small_region}
            selected.append(row)
            subtype_counts[(row["primary_osm_key"], row["primary_osm_value"])] += 1
            seen_names.add(normalized(row["name"]))
            entity = raw_tags(row["raw_tags"]).get("wikidata", "")
            if entity:
                seen_entities.add(entity)
            seen_habitats.add(row["habitat_primary"])
            remaining = [r for r in remaining if r["poi_id"] != row["poi_id"]]
        for row in selected:
            distances = [points[row["poi_id"]].distance(points[s["poi_id"]]) * unit_meters
                         for s in selected if s["poi_id"] != row["poi_id"]]
            nearest = min(distances) if distances else None
            satisfied = nearest is None or nearest >= settings["preferred_spacing_meters"]
            row.update(nearest_selected_candidate_distance_m=nearest, spacing_preference_satisfied=satisfied,
                       spacing_reason="preferred_spacing" if satisfied else "small_region_relaxation",
                       same_subtype_shortlist_count=subtype_counts[(row["primary_osm_key"], row["primary_osm_value"])],
                       category_diversity_satisfied=True,
                       recommendation_rationale=(f"{row['specialization_reason']}; primary habitat is {row['region_primary_habitat_poi_share']:.0%} of regional POIs. "
                                                 f"{row['candidate_access_reason']} Human-review candidate only."))
            result.append(row)
    fields = list(scores.columns) + ["region_candidate_rank", "selection_priority_score", "new_habitat_at_selection",
        "spacing_relaxation_available", "nearest_selected_candidate_distance_m", "spacing_preference_satisfied",
        "spacing_reason", "same_subtype_shortlist_count", "category_diversity_satisfied", "recommendation_rationale"]
    return pd.DataFrame(result, columns=fields)


def validation(scores, shortlist, config):
    if len(scores) != config["expected_poi_count"] or scores.poi_id.duplicated().any():
        raise ValueError("Scoring changed canonical POI inventory")
    for field, bound in zip(SCORE_FIELDS, config["dimension_bounds"].values()):
        if not scores[field].between(0, bound).all():
            raise ValueError(f"Out-of-bounds scores: {field}")
    if not scores.raw_candidate_score.between(0, 100).all():
        raise ValueError("Candidate total outside 0-100")
    if (scores[SCORE_FIELDS].sum(axis=1)-scores.raw_candidate_score).abs().max() > 1e-6:
        raise ValueError("Candidate total differs from dimension sum")
    if shortlist.empty:
        return
    if not shortlist.candidate_eligible.all() or shortlist.candidate_access_status.eq("restricted_or_inappropriate").any():
        raise ValueError("Ineligible/restricted candidate entered shortlist")
    if not shortlist.habitat_primary.isin(config["habitats"]).all() or shortlist.poi_id.duplicated().any():
        raise ValueError("Invalid shortlist identity or habitat")
    if shortlist.groupby("region_id").size().max() > config["shortlist"]["max_per_region"]:
        raise ValueError("Too many shortlisted candidates")
    if shortlist.groupby(["region_id", "primary_osm_key", "primary_osm_value"]).size().max() > config["shortlist"]["maximum_same_subtype"]:
        raise ValueError("Shortlist subtype cap exceeded")


def write_outputs(scores, shortlist, regions, config):
    selected = set(shortlist.poi_id)
    strong = (scores.raw_candidate_score >= config["shortlist"]["minimum_raw_score"]) & (scores.specialization_score >= config["shortlist"]["minimum_specialization_score"])
    scores = scores.copy()
    scores["shortlist_status"] = ["shortlisted" if pid in selected else "ineligible" if not eligible
                                  else "below_quality_threshold" if not high else "diversity_or_spacing_limit"
                                  for pid,eligible,high in zip(scores.poi_id, scores.candidate_eligible, strong)]
    # Record final-set constraints for non-selected candidates without changing their score.
    distances, selection_reasons = [], []
    valid_points, valid_ids = [], []
    for row in scores.itertuples():
        try:
            lon, lat = float(row.representative_longitude), float(row.representative_latitude)
            if math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90:
                valid_points.append(Point(lon,lat))
                valid_ids.append(row.poi_id)
        except (ValueError,TypeError):
            pass
    points = gpd.GeoSeries(valid_points, index=valid_ids, crs=4326).to_crs(config["analysis_crs"])
    unit_meters = points.crs.axis_info[0].unit_conversion_factor
    for row in scores.itertuples():
        picked = shortlist[(shortlist.region_id == row.region_id) & (shortlist.poi_id != row.poi_id)]
        nearest = min((points[row.poi_id].distance(points[pid]) * unit_meters for pid in picked.poi_id), default=None) if row.poi_id in points.index else None
        distances.append(nearest)
        reasons = []
        if row.poi_id not in selected:
            if not row.candidate_eligible:
                reasons.append("ineligible:" + row.candidate_exclusion_reason)
            else:
                if row.raw_candidate_score < config["shortlist"]["minimum_raw_score"]:
                    reasons.append("below_minimum_raw_score")
                if row.specialization_score < config["shortlist"]["minimum_specialization_score"]:
                    reasons.append("below_minimum_specialization")
                if not reasons:
                    if len(picked) >= config["shortlist"]["max_per_region"]:
                        reasons.append("region_shortlist_cap")
                    same_type = (picked.primary_osm_key == row.primary_osm_key) & (picked.primary_osm_value == row.primary_osm_value)
                    if same_type.sum() >= config["shortlist"]["maximum_same_subtype"]:
                        reasons.append("subtype_cap")
                    if normalized(row.name) in set(picked.name.map(normalized)):
                        reasons.append("repeated_venue_name")
                    entity = raw_tags(row.raw_tags).get("wikidata", "")
                    if entity and entity in {raw_tags(v).get("wikidata") for v in picked.raw_tags}:
                        reasons.append("repeated_wikidata_entity")
                    if nearest is not None and nearest < config["shortlist"]["preferred_spacing_meters"]:
                        reasons.append("preferred_spacing_conflict")
                    if not reasons:
                        reasons.append("lower_selection_priority")
        selection_reasons.append(";".join(reasons))
    scores["nearest_shortlisted_candidate_distance_m"] = distances
    scores["shortlist_exclusion_reason"] = selection_reasons
    interest = ((scores.raw_candidate_score >= config["review"]["minimum_interesting_raw_score"])
                | (scores.specialization_score >= config["review"]["minimum_interesting_specialization"]))
    review = scores[scores.candidate_review_required & interest].copy()
    scores.to_csv(DATA / "special_poi_candidate_scores.csv", index=False)
    shortlist.to_csv(DATA / "special_poi_candidates_by_region.csv", index=False)
    review.to_csv(DATA / "special_poi_candidate_review_queue.csv", index=False)
    summaries = []
    for region in regions.sort_values("region_id").itertuples():
        part = scores[scores.region_id == region.region_id]
        picked = shortlist[shortlist.region_id == region.region_id]
        summaries.append({"region_id": region.region_id, "parent_city": region.parent_city,
                          "total_pois": len(part), "eligible_candidate_pois": int(part.candidate_eligible.sum()),
                          "excluded_pois": int((~part.candidate_eligible).sum()),
                          "access_uncertain_candidates": int((part.candidate_eligible & part.candidate_access_status.eq("public_context_access_uncertain")).sum()),
                          "quality_threshold_candidates": int((part.candidate_eligible & strong.loc[part.index]).sum()),
                          "shortlist_size": len(picked),
                          "shortlist_habitat_distribution": json.dumps(picked.habitat_primary.value_counts().to_dict(), sort_keys=True),
                          "shortlist_average_raw_score": picked.raw_candidate_score.mean() if len(picked) else None,
                          "spacing_preference_unmet_count": int((~picked.spacing_preference_satisfied).sum()) if len(picked) else 0,
                          "unshortlisted_strong_spacing_conflicts": int(part.shortlist_exclusion_reason.str.contains("preferred_spacing_conflict").sum()),
                          "weak_candidate_coverage": len(picked) < config["shortlist"]["weak_coverage_below_count"]})
    summary = pd.DataFrame(summaries)
    summary.to_csv(DATA / "special_poi_candidate_summary.csv", index=False)
    return scores, review, summary


def maps(shortlist, regions, zones):
    OUTPUT.mkdir(exist_ok=True)
    for city in ["Raleigh", "Durham"]:
        parents = regions[regions.parent_city == city].to_crs(2264)
        backdrop = zones[zones.parent_city == city].to_crs(2264)
        picked = shortlist[shortlist.parent_city == city]
        points = gpd.GeoDataFrame(picked.copy(), geometry=[Point(r.representative_longitude, r.representative_latitude)
                                  for r in picked.itertuples()], crs=4326).to_crs(2264)
        fig, ax = plt.subplots(figsize=(14, 10))
        backdrop.plot(ax=ax, column="habitat_primary", cmap="Set3", alpha=0.22, edgecolor="#999999", linewidth=0.3)
        parents.boundary.plot(ax=ax, color="#222222", linewidth=1)
        for region in parents.itertuples():
            p = region.geometry.representative_point()
            offset = {"RAL-01": (25,20), "RAL-03B": (0,-26)}.get(region.region_id, (0,-18))
            ax.annotate(region.region_id, (p.x,p.y), xytext=offset, textcoords="offset points", ha="center", fontsize=9, weight="bold")
        for status,color,label in [("likely_public", "#176b48", "Likely public"),
                                    ("public_context_access_uncertain", "#c36d13", "Access uncertain; review")]:
            part = points[points.candidate_access_status == status]
            if not part.empty:
                part.plot(ax=ax, color=color, edgecolor="white", linewidth=0.7, markersize=70, zorder=4)
        for i,row in enumerate(points.itertuples()):
            ax.annotate(str(row.region_candidate_rank), (row.geometry.x,row.geometry.y),
                        xytext=(6,6 if i%2 else -10), textcoords="offset points", fontsize=8,
                        bbox={"facecolor":"white","edgecolor":"none","alpha":0.8,"pad":0.5}, zorder=5)
        handles = [Line2D([0],[0],marker="o",color="none",markerfacecolor=color,label=label,markersize=7)
                   for color,label in [("#176b48","Likely public"),("#c36d13","Access uncertain; review")]]
        ax.legend(handles=handles, loc="upper right", fontsize=9)
        ax.set_title(f"{city}: Special POI Candidate Review (Numbers = Rank Within Region)")
        ax.set_axis_off(); fig.tight_layout()
        fig.savefig(OUTPUT / f"special_poi_candidates_{city.lower()}.png", dpi=180)
        plt.close(fig)


def markdown_table(frame):
    lines = ["| " + " | ".join(frame.columns) + " |", "| " + " | ".join(["---"]*len(frame.columns)) + " |"]
    for row in frame.itertuples(index=False, name=None):
        values = [f"{v:.2f}" if isinstance(v,float) else str(v) for v in row]
        lines.append("| " + " | ".join(v.replace("|", "\\|") for v in values) + " |")
    return "\n".join(lines)


def report(scores, shortlist, review, summary, config, before):
    excluded = Counter(reason for value in scores.candidate_exclusion_reason for reason in value.split(";") if reason)
    lines = ["# Special POI Candidate Review", "", "Candidates for human review only. No final special locations or rarity pools are assigned.", "",
             f"Evaluated: {len(scores)}; eligible: {int(scores.candidate_eligible.sum())}; excluded: {int((~scores.candidate_eligible).sum())}; review queue: {len(review)}.", "",
             "## Exclusion Reasons", "", json.dumps(dict(excluded), indent=2), "",
             "## Access Status", "", markdown_table(scores.candidate_access_status.value_counts().rename_axis("status").reset_index(name="count")), "",
             "## Regional Summary", "", markdown_table(summary), ""]
    for rid in sorted(config["canonical_region_ids"]):
        part = shortlist[shortlist.region_id == rid]
        lines += [f"## {rid}", "", markdown_table(part[["region_candidate_rank", "name", "habitat_primary", "habitat_secondary", "raw_candidate_score", "candidate_access_status", "nearest_selected_candidate_distance_m", "recommendation_rationale"]]), ""]
    spacing = shortlist[~shortlist.spacing_preference_satisfied] if len(shortlist) else shortlist
    spacing_conflicts = scores[scores.shortlist_exclusion_reason.str.contains("preferred_spacing_conflict")].sort_values(
        ["region_id", "raw_candidate_score", "poi_id"], ascending=[True, False, True])
    restricted = scores[(scores.candidate_access_status == "restricted_or_inappropriate") &
                        (scores.raw_candidate_score >= config["review"]["high_scoring_restricted_threshold"])]
    lines += ["## Spacing Exceptions", "", markdown_table(spacing[["region_id", "name", "nearest_selected_candidate_distance_m", "spacing_reason"]]), "",
              "## Strong Unshortlisted Candidates with Spacing Conflicts", "",
              markdown_table(spacing_conflicts[["region_id", "name", "raw_candidate_score", "nearest_shortlisted_candidate_distance_m", "shortlist_exclusion_reason"]]), "",
              "These are final-set conflicts, not claims that spacing was the sole cause of exclusion. Category/venue limits and the region cap may also apply. Scores are not lowered to force a larger shortlist.", "",
              "## High-scoring Restricted Candidates (Excluded)", "", markdown_table(restricted[["region_id", "name", "raw_candidate_score", "candidate_access_reason"]]), "",
              "## Weak Coverage", "", markdown_table(summary[summary.weak_candidate_coverage]), "",
              "## Canonical Input Integrity", "", f"{len(before)} protected files retain identical SHA-256 hashes. See special_poi_candidate_provenance.json.", "",
              "![Raleigh candidate QA](special_poi_candidates_raleigh.png)", "![Durham candidate QA](special_poi_candidates_durham.png)"]
    (OUTPUT / "special_poi_candidate_report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    (OUTPUT / "special_poi_candidate_provenance.json").write_text(json.dumps({
        "config_version": config["version"], "canonical_inputs_unchanged": True,
        "protected_input_sha256": before, "evaluated_pois": len(scores), "eligible_candidates": int(scores.candidate_eligible.sum()),
        "shortlisted_candidates": len(shortlist), "review_queue_candidates": len(review),
    }, indent=2)+"\n", encoding="utf-8")


def main():
    with CONFIG.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if list(config["dimension_bounds"].values()) != [35,25,20,20]:
        raise ValueError("Expected the four approved scoring bounds")
    before = input_hashes()
    pois, regions, zones, neutral = load_inputs(config)
    context = build_context(pois, regions, zones, neutral, config)
    scores = score_all(pois, context, config)
    shortlist = shortlist_candidates(scores, regions, config)
    validation(scores, shortlist, config)
    scores, review, summary = write_outputs(scores, shortlist, regions, config)
    maps(shortlist, regions, zones)
    if input_hashes() != before:
        raise RuntimeError("Canonical inputs changed during candidate scoring")
    report(scores, shortlist, review, summary, config, before)
    print(summary.to_string(index=False))
    print(f"Evaluated {len(scores)}; eligible {int(scores.candidate_eligible.sum())}; shortlisted {len(shortlist)}; review queue {len(review)}")


if __name__ == "__main__":
    main()
