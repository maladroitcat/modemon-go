# Modedex Workbook Links: Research Only

Issue #26 proposal, pending product-owner review. No game screens, canonical
Modedex content, quiz answers, assets, geography, or Signature evidence changed.
This branch is independent of the camera-preference implementation in issue #25.

## Review Artifacts

- [51-row mapping](research/modedex_learning_mapping.md): every canonical species,
  its represented job, precise lesson title/link, rationale, confidence, boundary,
  and independently justified secondary lesson where useful.
- [Canonical inventory and mapping CSV](research/modedex_learning_inventory.csv):
  also includes the unchanged `family_id`, `stage`, `role`, `ai_tasks`,
  `models_algorithms`, `input_data`, `output_data`, habitats, explanation methods,
  and limitations. These are the actual source field names; there are no invented
  `model_family`, `algorithms`, `inputs`, or `outputs` fields in canon.
- [Review queue](research/modedex_learning_review_queue.csv): partial and
  unresolved matches. An unresolved entry intentionally has no primary URL.
- [Separate editable overlay](config/modedex_learning_links.yaml): one keyed
  decision per canonical species plus a shared exact-lesson catalog. Resolving
  catalog references gives the full title, workbook, unit, chapter, and URL.
- [Live verification](research/workbook_lesson_verification.json): HTTP status,
  final URL, actual article H1, live TOC membership, inspected content terms,
  body-text hash, and UTC verification time. No lesson bodies are republished.
- [TOC discovery inventory](research/workbook_toc_inventory.json): exact links
  found while inspecting all 15 live unit tables of contents across the three
  authorized workbooks. This records the search surface, not proof that no future
  lesson could fill a gap.

## Selection Method

Research was performed October 18, 2026. Discovered exact article links from
the live workbooks, read their body content, checked the actual H1/topic coverage,
and matched against each species' documented job, input/output and representative
techniques. HTTP success alone is not a relevance test. No homepage placeholders,
fabricated chapter slugs, or links outside the three owner-authorized sites are
proposed. The verification helper checks only these domains over HTTPS, identifies
the application, and spaces requests; regular tests are offline.

High confidence means a direct task, input-representation concept, or explicitly
canonical representative technique. It does **not** mean a lesson covers every
algorithm in that record. Foundational articles are preferred for common forms.
Medium means partial technique or related-context coverage that needs review;
low means unresolved. Every row records what the lesson does **not** establish.
Optional second articles add a distinct purpose such as explaining a prediction,
preserving lineage, or understanding a retrieval index, not extra link volume.

Specific caveats worth owner attention:

- Scheduling: neural-network optimizers and data-pipeline DAG orchestration are
  not vehicle routing, mixed-integer programming, or operational staff scheduling.
  Wardray, Routeopus, Flowfin, Cabcrab, Shiftshark and Parcelprawn remain unresolved.
  Plancton has a partial RL match because RL is explicitly canonical; Signalquid
  has a partial perception-subtask match, not a traffic-control algorithm lesson.
- Extraction: Scribbit, Clinink, Bureaucritter, Manusqueak and Specimunk remain
  unresolved. General NLP is not OCR, clinical entity extraction, layout analysis,
  or handwriting recognition. Scholarat has an explicit topic-modeling match;
  Archivole's thematic-text-analysis match is only contextual and needs review.
- Time Series is an accessible input foundation, not an ARIMA tutorial. Temporal
  features explain model inputs, not forecasting accuracy. The LSTM secondary
  teaches an explicitly canonical architecture in NLP framing, not a transit
  implementation.
- Generic LLM coverage is partial for Muselect, Mentamorph and Catalogar where
  specialized curation, adaptive learning, or catalog standards are not taught.
- Geargoyle's autoencoder lesson explains reconstruction, but not anomaly
  thresholds or maintenance decisions; Netnark has no network-security-specific
  article. Both stay in review.

## Signature Claim Boundary

Workbook links are educational supporting material, **not evidence about a
Signature project's deployed architecture or exact location**. The inventory
keeps all 12 original `signature.source_url` values in a separate
`signature_project_source_url` column. These research links never replace them.
Cabcrab is not assumed to use an LLM; Signalquid is not assumed to use YOLO.
No research finding authorizes a new deployment claim, spawn, or POI mapping.

## Reproduction and Checks

From the repository root with the existing Python requirements installed:

```sh
# Explicit network audit; run when refreshing the research, not on every test.
python3 -B scripts/audit_workbook_lessons.py --output data/research/workbook_lesson_verification.json
# Optional new TOC discovery snapshot (network):
python3 -B scripts/audit_workbook_lessons.py --discover --output data/research/workbook_toc_inventory.json
# Deterministic offline review artifacts; no app data is written:
python3 -B -m scripts.build_workbook_research_review
python3 -B -m unittest discover -s tests -v
```

`modedex_learning_source_hashes.json` records every pre-existing configuration and
processed canonical file; render checks before/after hashes and tests compare the
committed baseline. CSV inventory values are joined directly from canon, not
manually rewritten. Live verification can change over time; offline tests prove
snapshot consistency, not permanent future site availability.

## Review Decisions Needed

Approve or revise the 51-row proposal before any UI integration. In particular,
decide whether partial concept links should be shown with a narrower label, or
withheld until direct lessons exist. The 11 unresolved species must not acquire
generic fallback links merely to achieve 100% coverage. Candidate lessons on an
unresolved row are review leads, not recommended or active links. Whether and how
undiscovered Modedex entries show future links remains a separate product decision.

## Attribution

Sources: [Explainable AI Workbook](https://explainableaiworkbook.com/),
[Data Science Workbook](https://datascienceworkbook.com/), and
[Deep Learning Workbook](https://deeplearningworkbook.com/), maintained by
Dr. Brinnae Bent. See each site's current attribution/license notices. This
research links to original lessons and stores titles, discovery metadata, and
verification hashes, not copies of the lessons. Relevance rationales are project
research judgments and should not imply workbook-author endorsement.
