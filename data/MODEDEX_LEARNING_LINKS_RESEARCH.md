# Modedex Workbook Links: Research Only

Issue #26 proposal, pending product-owner review. No game screens, canonical
Modedex content, quiz answers, assets, geography, or Signature evidence changed.
Camera and gameplay behavior are outside this research branch's scope.

## Review Artifacts

- [Table A: 51-row preferred-workbook mapping](research/modedex_learning_mapping.md): every canonical species,
  its represented job, precise lesson title/link, rationale, confidence, boundary,
  and independently justified secondary lesson where useful.
- [Table B: external fallback review](research/modedex_external_owner_review.md)
  and its [CSV](research/modedex_external_owner_review.csv): six proposals using
  five distinct verified sources. **EVERY row is `PENDING_OWNER_APPROVAL`.**
  These are not approved mappings and never fill the workbook table's blanks.
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
- [Full corpus audit](research/workbook_full_review.json): all 360 unique
  discovered lesson bodies were fetched and indexed: 123 Explainable AI,
  121 Data Science, and 116 Deep Learning. Contains headings, hashes, timestamps
  and topic-term counts, not copies of the articles.
- [21-species component review](research/workbook_component_review.yaml): every
  previously unresolved/partial entry, alternatives considered, resulting scope,
  and rejected misleading keyword matches.
- [Pending external proposals](research/modedex_external_proposals.yaml) and
  [verification evidence](research/external_reference_verification.json): titles,
  publishers, exact URLs, topic checks, hashes and timestamps. Verification does
  not authorize use; even two species sharing a URL require individual approval.

## Selection Method

Research and the expanded source-policy review were performed October 18, 2026.
The second pass fetched/indexed the full main-body content of all 360 lessons
discovered from all three homepages and their 15 linked unit TOCs, then reviewed
relevant hits and competing component explanations for all 21 prior weak/gap
entries. Topic terms are search leads, not an automatic classifier or proof of
relevance. Domain-restricted search and sitemap checks revealed no extra lesson
URLs; see the discovery limitations in the component-review file. No lesson
fetches remain unresolved. This is exhaustive for the public discovered corpus,
not a claim about unpublished or undiscoverable pages.

Matched the actual article title and subject against each species' unchanged
job, inputs/outputs and canonical techniques. HTTP success alone is insufficient.
There are no homepage placeholders or invented chapter slugs. Preferred-workbook
and external audits use separate helpers and artifacts; neither ships links.
Requests are identified and paced. Regular tests are offline.

High confidence means a direct task, input-representation concept, or explicitly
canonical representative technique. It does **not** mean a lesson covers every
algorithm in that record. Foundational articles are preferred for common forms.
Medium includes genuine component, foundation or related-context coverage that needs review;
low means unresolved. Every row records what the lesson does **not** establish.
Optional second articles add a distinct purpose such as explaining a prediction,
preserving lineage, or understanding a retrieval index, not extra link volume.

Specific caveats worth owner attention:

- Five former gaps now have scoped workbook proposals: Scribbit (entity-tagging
  illustration), Clinink (encoder text understanding), Bureaucritter (transformer
  interpretation foundation), Manusqueak (multimodal inputs), and Flowfin
  (temporal features for a predictive component). None claims complete system
  coverage. The narrowest foundations especially need owner review.
- Specimunk, Wardray, Routeopus, Cabcrab, Shiftshark and Parcelprawn remain blank
  in Table A. Table B proposes external teaching material for these genuine gaps.
- Scheduling: neural optimizer updates, token/expert routing, HTTP routing and
  data-pipeline DAG ordering are not operational vehicle or staff allocation.
  A workbook's one-line MILP mention in neural robustness verification does not
  teach assignment objectives and constraints. Plancton's explicit RL component
  and Signalquid's perception component remain legitimate scoped matches.
- NER, contextual encoders and multimodal inputs are valid components, but do not
  teach all of clinical extraction, scanned-page layout or handwriting. The RNN
  in Scribbit's lesson illustrates an entity-tagging task; it is not a new
  assertion about canonical representative algorithms. Scholarat's topic model
  is explicitly canonical; Archivole's theme-analysis example is not a claim
  about the redlining project's undisclosed implementation.
- Time Series is an accessible input foundation, not an ARIMA tutorial. Temporal
  features explain model inputs, not forecasting accuracy. The LSTM secondary
  teaches an explicitly canonical architecture in NLP framing, not a transit
  implementation.
- LLM coverage remains component-level for Muselect, Mentamorph and Catalogar,
  not a complete curation/adaptive-learning/catalog-standards tutorial. Muselect
  now has a separate prompt-inspection lesson; Catalogar has an agent-audit lesson.
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
# Exhaustive preferred-source pass (article cache must remain outside Git):
python3 -B -m scripts.review_workbook_coverage --cache-dir /private/tmp/modemon-workbook-full-review
# Explicit network audit; run when refreshing the research, not on every test.
python3 -B scripts/audit_workbook_lessons.py --output data/research/workbook_lesson_verification.json
# Optional new TOC discovery snapshot (network):
python3 -B scripts/audit_workbook_lessons.py --discover --output data/research/workbook_toc_inventory.json
# Deterministic offline review artifacts; no app data is written:
python3 -B -m scripts.build_workbook_research_review
# Separate pending-external live audit, then Table B rendering:
python3 -B -m scripts.review_external_learning_references --verify
# Offline Table B rendering (no network or approval):
python3 -B -m scripts.review_external_learning_references
python3 -B -m unittest discover -s tests -v
```

The live external PDF audit additionally requires optional `pypdf` (research used
6.14.2). It is not imported for offline rendering or tests. No app dependency or
runtime package was added. Unexpected source redirects or content/title changes
fail the live check instead of silently choosing a replacement.

`modedex_learning_source_hashes.json` records every pre-existing configuration and
processed canonical file; render checks before/after hashes and tests compare the
committed baseline. CSV inventory values are joined directly from canon, not
manually rewritten. Live verification can change over time; offline tests prove
snapshot consistency, not permanent future site availability.

## Review Decisions Needed

Table A now has 45 proposed workbook matches, six deliberate blanks, and 21
review rows; confidence remains 30 high, 15 medium and six low. All 51 species
remain inventoried. Owner policy permits genuinely useful components, not a
claim that every component lesson explains an entire deployed AI system.

Review component scope labels and accept/revise the 51-row proposal before UI
integration. Decide whether narrower future labels such as "Learn about this
component" are appropriate; no existing UI copy is changed here. Then approve or
reject each Table B species/reference pair individually (or request alternates).
Every external reference, including verified ones, is `PENDING_OWNER_APPROVAL`.
The research validator rejects attempts to call a proposal approved or shipped.
It cannot apply proposals to the Modedex. A later explicitly authorized change
would be needed to integrate any owner-approved external link.

The six gaps stay unpopulated until approval; candidate leads are not active
links. No mathematical score or desire for 100% coverage overrides this gate.
Undiscovered-entry link visibility remains a separate UI decision. Nothing in
this branch is deployed or automatically merged.

## Attribution

Sources: [Explainable AI Workbook](https://explainableaiworkbook.com/),
[Data Science Workbook](https://datascienceworkbook.com/), and
[Deep Learning Workbook](https://deeplearningworkbook.com/), maintained by
Dr. Brinnae Bent. See each site's current attribution/license notices. This
research links to original lessons and stores titles, discovery metadata, and
verification hashes, not copies of the lessons. External proposals attribute
Google's OR-Tools documentation, Hugging Face's Transformers documentation, and
Jurafsky and Martin's Stanford-hosted textbook draft separately in Table B; their
licenses and attribution requirements require review before reuse. We propose
links, not republication of their material. Relevance rationales are project
research judgments and do not imply source-author endorsement.
