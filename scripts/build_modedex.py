#!/usr/bin/env python3
"""Validate human-maintained Modedex YAML and build deterministic application JSON."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from rfc3986_validator import validate_rfc3986
import yaml
from yaml.constructor import ConstructorError
from yaml.resolver import BaseResolver

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data/config/modedex.yaml"
SCHEMA_PATH = ROOT / "data/schema/modedex.schema.json"
OUTPUT_PATH = ROOT / "data/processed/modedex.json"
FAMILY_IDS = frozenset({
    "detector", "anomaly", "forecast", "recommender", "extractor",
    "scheduler", "generator", "retriever",
})
STAGE_COUNTS = {1: 8, 2: 31, 3: 12}
RARITIES = {1: "common", 2: "rare", 3: "signature"}


class ModedexValidationError(ValueError):
    """Invalid source content; no output should be written."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Do not let YAML silently overwrite duplicate records or fields."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise ConstructorError(None, None, "YAML merge keys are not supported; write explicit records", key_node.start_mark)
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise ConstructorError(None, None, "Modedex mapping keys must be strings", key_node.start_mark)
        if key in result:
            raise ConstructorError(None, None, f"Duplicate YAML key {key!r}", key_node.start_mark)
        result[key] = loader.construct_object(value_node)
    return result


UniqueKeyLoader.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def load_yaml(path=SOURCE_PATH):
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as stream:
            return yaml.load(stream, Loader=UniqueKeyLoader)
    except yaml.YAMLError as error:
        raise ModedexValidationError(f"Invalid YAML in {path}: {error}") from error


def load_schema(path=SCHEMA_PATH):
    with Path(path).open(encoding="utf-8") as stream:
        schema = json.load(stream)
    Draft202012Validator.check_schema(schema)
    return schema


def format_checker():
    checker = FormatChecker()

    # URI support is optional in jsonschema; register the pinned RFC validator explicitly.
    @checker.checks("uri")
    def uri(value):
        return not isinstance(value, str) or validate_rfc3986(value, rule="URI") is not None

    return checker


def validate_structure(document, schema):
    validator = Draft202012Validator(schema, format_checker=format_checker())
    errors = sorted(validator.iter_errors(document), key=lambda e: (
        tuple(str(part) for part in e.absolute_path), e.message))
    if errors:
        messages = [f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors]
        raise ModedexValidationError("JSON Schema validation failed:\n- " + "\n- ".join(messages))


def validate_semantics(document):
    """Check cross-record relationships after structural validation has succeeded."""
    families, modemon = document["families"], document["modemon"]
    errors = []
    if set(families) != FAMILY_IDS:
        errors.append("Expected exactly the eight canonical family IDs")
    if len(modemon) != 51:
        errors.append(f"Expected exactly 51 Modemon, found {len(modemon)}")
    counts = Counter(record["stage"] for record in modemon.values())
    if counts != STAGE_COUNTS:
        errors.append(f"Expected stage counts {STAGE_COUNTS}, found {dict(sorted(counts.items()))}")

    for family_id, family in families.items():
        bases = [key for key, record in modemon.items() if record["family_id"] == family_id and record["stage"] == 1]
        if len(bases) != 1:
            errors.append(f"families.{family_id}: expected exactly one base, found {len(bases)}")
        base_id = family["base_modemon_id"]
        if base_id not in modemon:
            errors.append(f"families.{family_id}.base_modemon_id: unknown Modemon {base_id!r}")
        elif base_id not in bases:
            errors.append(f"families.{family_id}.base_modemon_id: must identify its own family's stage-1 base")

    # Check cycles independently, rather than assuming stage checks rule them out.
    visited, active = set(), []

    def visit(modemon_id):
        if modemon_id in active:
            cycle = active[active.index(modemon_id):] + [modemon_id]
            errors.append("Evolution cycle: " + " -> ".join(cycle))
            return
        if modemon_id in visited:
            return
        active.append(modemon_id)
        parent_id = modemon[modemon_id]["evolves_from"]
        if parent_id in modemon:
            visit(parent_id)
        active.pop()
        visited.add(modemon_id)

    for modemon_id in sorted(modemon):
        visit(modemon_id)

    for modemon_id, record in modemon.items():
        path = f"modemon.{modemon_id}"
        family_id, stage, parent_id = record["family_id"], record["stage"], record["evolves_from"]
        if family_id not in families:
            errors.append(f"{path}.family_id: unknown family {family_id!r}")
        if not modemon_id.startswith(family_id + "_"):
            errors.append(f"{path}: stable ID must start with its family ID and an underscore")
        if record["rarity"] != RARITIES[stage]:
            errors.append(f"{path}.rarity: stage {stage} requires {RARITIES[stage]!r}")
        if stage == 1:
            if parent_id is not None:
                errors.append(f"{path}.evolves_from: a base must have no parent")
        elif parent_id not in modemon:
            errors.append(f"{path}.evolves_from: unknown parent {parent_id!r}")
        else:
            parent = modemon[parent_id]
            if parent["stage"] != stage - 1:
                errors.append(f"{path}.evolves_from: stage {stage} requires a stage-{stage - 1} parent")
            if parent["family_id"] != family_id:
                errors.append(f"{path}.evolves_from: parent must belong to the same family")
        signature = record["signature"]
        if (stage == 3) != (signature is not None):
            errors.append(f"{path}.signature: only stage 3 requires Signature metadata")
        if signature is not None:
            url = signature["source_url"]
            try:
                parts = urlsplit(url)
                web_source = parts.scheme in {"http", "https"} and bool(parts.hostname)
            except ValueError:
                web_source = False
            if not web_source:
                errors.append(f"{path}.signature.source_url: expected an absolute HTTP(S) source URL")
    if errors:
        raise ModedexValidationError("Semantic validation failed:\n- " + "\n- ".join(errors))


def validate(document, schema=None):
    schema = load_schema() if schema is None else schema
    validate_structure(document, schema)
    validate_semantics(document)


def build(source_path=SOURCE_PATH, output_path=OUTPUT_PATH, schema_path=SCHEMA_PATH):
    source_path, output_path, schema_path = map(Path, (source_path, output_path, schema_path))
    if output_path.resolve() in {source_path.resolve(), schema_path.resolve()}:
        raise ModedexValidationError("Output must not overwrite the canonical YAML or JSON Schema")
    document = load_yaml(source_path)
    validate(document, load_schema(schema_path))
    encoded = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(encoded, encoding="utf-8")
    return document


def main():
    try:
        document = build()
    except (ModedexValidationError, OSError, json.JSONDecodeError) as error:
        print(f"Modedex build failed: {error}", file=sys.stderr)
        return 1
    print(f"Built {OUTPUT_PATH.relative_to(ROOT)}: {len(document['families'])} families, {len(document['modemon'])} Modemon, stages {dict(sorted(Counter(r['stage'] for r in document['modemon'].values()).items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
