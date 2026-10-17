# Canonical Modedex

The Modedex is educational content about recognizable real-world jobs, their AI
tasks, representative techniques, data, limitations, and ways to explain results.
It contains 8 families and 51 Modemon. It is not spawn configuration, a gameplay
engine, an asset manifest, or a claim about AI deployment at a map coordinate.

## Source and generated artifact

```text
data/config/modedex.yaml
        |
scripts/build_modedex.py + data/schema/modedex.schema.json
        |
data/processed/modedex.json
```

**YAML is the human-edited source of truth. JSON is generated; do not hand-edit
it.** The initial canonical YAML was copied verbatim from the supplied root
`modedex.yaml`, which is left untouched as an import reference, not a second
maintained source. No supplied names, IDs, prose, relationships, anchors, URLs,
or documented technology were changed. No additional web verification was done.

The top-level keys are exactly `version`, `families`, and `modemon`. Both families
and creatures are keyed mappings, not arrays. Each key under `modemon` is the
stable **modemon_id**; it is not redundantly stored inside its record. Application
lookups use `modedex.modemon[modemon_id]`.

## IDs, stages, and rarity

IDs describe semantic roles, such as `detector_base` or `extractor_specimen`.
They intentionally differ from display names, so renaming a creature does not
break references. No IDs were renamed. IDs use lower-case snake case prefixed
by their family ID. Families are `detector`, `anomaly`, `forecast`, `recommender`,
`extractor`, `scheduler`, `generator`, and `retriever`.

| Stage | Meaning | Rarity | Count | Parent |
|---|---|---|---:|---|
| 1 | Base capability | common | 8 | null |
| 2 | Domain-specific evolution | rare | 31 | Stage 1, same family |
| 3 | Signature evolution | signature | 12 | Stage 2, same family |

Rarity here is a content label, **not a probability**. Stage 1 and 2 records have
`signature: null`. Stage 3 records require the full Signature object. Each family
has exactly one stage-1 base and a `base_modemon_id` pointing to it. The sole
evolution relationship is `evolves_from`; consumers derive children by finding
records referencing a given ID. No separate evolution tree or mechanics exist.

Future spawn data should reference `modemon_id`, not `name`. Future artwork should
use those same stable IDs in filenames or references, not creature display names.
Neither spawn logic nor artwork is implemented by this data layer.

## Representation and examples

Independent lists are YAML arrays: `habitats`, `ai_tasks`, `models_algorithms`,
`biases_limitations`, `explainability`, and `signature.documented_technology`.
Do not encode lists with slashes or semicolons. `input_data` and `output_data` are
separate prose strings; `input_output` is rejected. Prose punctuation is retained.
Lists must be non-empty except `documented_technology`, which may be empty when
the source does not identify technology. All text and list items must be nonblank.

The following are **field excerpts**, not complete records; every required field
is present in the canonical YAML:

```yaml
families:
  detector:
    name: Detector
    base_modemon_id: detector_base
    visual_family: eyeball_scanner
    core_job: Recognize or locate things

modemon:
  detector_base:
    name: Seeklet
    family_id: detector
    stage: 1
    rarity: common
    evolves_from: null
    role: General Detector
    habitats:
      - healthcare
      - transportation
      - retail
      - food_hospitality
    input_data: Images and video frames
    output_data: Labels, object locations, segmentation masks, and confidence scores
    signature: null

  extractor_specimen:
    name: Specimunk
    family_id: extractor
    stage: 3
    rarity: signature
    evolves_from: extractor_archive
    role: Specimen Transcriber
    signature:
      anchor_name: NC Museum of Natural Sciences
      anchor_scope: institution
      verified_use: AI-assisted transcription of handwritten fish specimen records
      documented_technology: []
      source_title: Museum, UNC Use AI to Transform Handwritten Records About Fish
      source_organization: NC Museum of Natural Sciences
      source_url: https://www.naturalsciences.org/calendar/news/museum-unc-use-ai-to-transform-handwritten-records-about-fish/
```

Habitat IDs are exactly `healthcare`, `finance`, `retail`, `food_hospitality`,
`education_research`, `transportation`, `civic_government`, `entertainment`, and
`office_business`. These reference the established taxonomy without changing
existing POI habitat assignments, scores, cells, or zones.

## Signature evidence and claim boundaries

A Signature form connects an educational task to a documented real-world example.
Its `signature` records the anchor, scope, verified use, documented technology,
source title, organization, and source URL. This does not imply a current active
spawn, site-specific installation, or a newly verified deployment.

`models_algorithms` lists representative techniques commonly applicable to the
task. **It does not assert that an anchor uses those techniques.** In contrast,
`signature.documented_technology` records only what the supplied public source
identifies. Empty arrays intentionally preserve uncertainty; never fill them by
guessing an OCR architecture or other undocumented model.

Association anchors are not exact-coordinate deployment claims. Durham Station
can anchor GoDurham system-level educational content, and RUS BUS can anchor
Raleigh transportation-system content. A museum, library, or university can
anchor institution-level or research-project content without implying the system
physically runs at that POI. Institution-level activity is not evidence that a
specific model runs at a player's exact location. Preserve these distinctions in
future content/UI; do not silently link Signature forms to individual destinations.

The builder checks syntax and consistency, not source availability, accuracy,
freshness, or physical access. Supplied sources and educational prose remain human
editorial responsibilities. No online source fetching is part of a build.

## Rebuild and validation

Use the project Python environment with `requirements.txt` installed:

```sh
python -m pip install -r requirements.txt
python -B scripts/build_modedex.py
python -B -m unittest discover -s tests -v
```

For the local environment created during implementation, use
`.venv/bin/python` in place of `python`.

Validation occurs before writing output:

1. Safe YAML loading rejects duplicate keys at any depth, non-string keys, and
   YAML merge keys. A repeated ID cannot silently overwrite another creature.
2. Draft 2020-12 JSON Schema validates exact object structure, required fields,
   stage/rarity/signature rules, enumerations, text and array types, and canonical
   habitat IDs. Unknown properties, including `input_output`, fail. URI format
   checking is explicitly enabled with the pinned RFC 3986 validator; it is not
   an ignored schema annotation.
3. Python checks the 8-family/51-creature inventory, 8/31/12 stage counts, unique
   family bases, same-family evolution references and prior stages, and cycles.
   Signature citations must be absolute HTTP(S) source URLs with a host. No
   missing or malformed records are repaired automatically.

Errors include record paths and cause a nonzero exit. Validation failure leaves
any previous generated JSON untouched. The builder writes only `modedex.json`;
it never reads or writes geographic or POI datasets.

JSON is UTF-8, pretty-printed with two-space indentation, object keys sorted,
array order preserved, and a final newline. There are no timestamps or injected
metadata. Builds from unchanged YAML are byte-identical; JSON equals the parsed
YAML structurally. Tests cover malformed records, relationships, counts, duplicate
keys, source URLs, content integrity, deterministic builds, and unchanged unrelated
files. Existing tests remain in the complete test suite.
