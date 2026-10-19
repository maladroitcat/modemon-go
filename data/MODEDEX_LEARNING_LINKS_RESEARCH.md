# Modedex Learning References and Approval Provenance

Issue #26 / merged PR #29 established the research mappings. Issue #30 approves
all four outside references and authorizes a validated non-Signature learning
overlay in the playable Modedex, plus deployment to the existing public preview.
This authorization does not permit automatic merging or canonical content edits.

## Approved Policy

- All **45 existing workbook matches** are preserved unchanged, including the
  original optional lessons, rationale, scope, confidence, and historical flags.
  Only top-level approval/implementation metadata changes.
- All **12 Signatures** retain **only their canonical real-project source link**
  in the UI. Existing Signature workbook matches remain research provenance, not
  supplementary player-facing links. No new Signature research is needed.
- **35 of 39 non-Signatures** have existing workbook matches. The other four
  use the owner's exact approved outside references below.
- Component lessons are labeled as supporting concepts, not descriptions of a
  complete system or proof of a specific deployment.
- New or changed references require fresh owner approval.

## Outside References

| Species | Publisher / exact article | Effective status |
|---|---|---|
| Wardray | MIT News: [Robot helps nurses schedule tasks on labor floor](https://news.mit.edu/2016/robot-helps-nurses-schedule-tasks-on-labor-floor-0713) | APPROVED_BY_OWNER |
| Routeopus | Optibus: [Can Artificial Intelligence Prevent Bus Bunching?](https://blog.optibus.com/transportation/can-artificial-intelligence-prevent-bus-bunching) | APPROVED_BY_OWNER via issue #30 |
| Shiftshark | IBM Think: [What is contact center workforce optimization?](https://www.ibm.com/think/topics/contact-center-workforce-optimization) | APPROVED_BY_OWNER |
| Parcelprawn | IBM Think: [What is dispatch management?](https://www.ibm.com/think/topics/dispatch-management) | APPROVED_BY_OWNER |

The [owner decision ledger](research/modedex_external_owner_decisions.yaml)
preserves the first three approvals against reviewed commit 79dd9ce. It also
preserves the historical hold on Routeopus's MIT trip-planning article, superseded
by issue #30's explicit approval of the direct Optibus replacement against merged
PR #29. Approval is bound to the species and exact URL, not merely a publisher.

The [outside proposal records](research/modedex_external_proposals.yaml) and
[Table B](research/modedex_external_owner_review.md) now accurately reflect all
four approvals. HTTP evidence retains its original pending status because
network verification cannot approve content; the ledger is the authority.

The hospital article is a dated research example, not current clinical deployment
evidence. Optibus's 2018 article is vendor-authored and focused on timetable
reliability, not all crew-scheduling constraints. IBM's explainers are also
vendor-authored and broader than scheduling. These limitations remain preserved
per reference. Not all automation or optimization is machine learning.

## Preserved Scope Accounting

The original 40-match inventory had 11 workbook blanks: three Signatures
(Specimunk, Flowfin, Cabcrab) and eight non-Signatures (Scribbit, Clinink,
Bureaucritter, Manusqueak, Wardray, Routeopus, Shiftshark, Parcelprawn).

The accepted PR #29 inventory has 45 matches. Its five scoped additions are
unchanged. Of six remaining workbook blanks, two are Signatures (Specimunk,
Cabcrab), already covered by canonical project provenance. The other four now
have approved outside references. No outside URL is inserted into a workbook
field. See [scope accounting](research/modedex_reference_scope.json).

## Artifacts and Implementation

- [Workbook YAML](config/modedex_learning_links.yaml): approved matches and
  non-Signature-only implementation authorization.
- [Table A](research/modedex_learning_mapping.md) and
  [inventory CSV](research/modedex_learning_inventory.csv): all original match
  values and canonical fields, including separate Signature project sources.
- [Table B CSV](research/modedex_external_owner_review.csv): exact outside titles,
  sources, URLs, scope, relevance, limitations, and owner-decision provenance.
- [Workbook verification](research/workbook_lesson_verification.json) and
  [outside verification](research/external_reference_verification.json): exact
  URLs, observed titles, HTTP results, content checks, hashes, and retrieval times.
  These snapshots do not guarantee future availability or confer approval.
- [Playable UI pipeline and QA](../mobile/web/LEARNING_LINKS.md):
  `scripts/build_modedex_learning.py` produces
  `mobile/web/src/data/learning.json`, keyed only by the 39 non-Signature IDs.
  The overlay is separate from canonical content and the gameplay fingerprint.

The existing discovery gate remains in force. Readings are visible in known
Modedex entries and encounter information, not a new route to undiscovered
identities. External links open safely in a separate tab with visible titles,
publisher names, and explicit scope.

## Historical Research

The previous preferred-source audit indexed 360 lessons across 15 public unit
TOCs: 123 Explainable AI, 121 Data Science, 116 Deep Learning. The
[TOC snapshot](research/workbook_toc_inventory.json),
[body-audit metadata](research/workbook_full_review.json),
[21-species review](research/workbook_component_review.yaml), and
[historical queue](research/modedex_learning_review_queue.csv) remain unchanged.
They document research history, not outstanding approval requests or instructions
to reassess accepted mappings. Former tutorial-oriented and supplementary
Signature proposals remain only in Git history.

## Reproduction

```sh
python3 -B -m scripts.build_workbook_research_review
python3 -B -m scripts.review_external_learning_references
python3 -B scripts/build_modedex_learning.py
python3 -B -m unittest discover -s tests -v
```

The first two helpers render approval/provenance reports; they cannot ship app
links or grant approval. The separate learning builder requires explicit issue
#30 authorization and exact approved references. CI rebuilds the committed JSON
and production builds check its input hashes. Optional explicit network refreshes
remain separate from approval; normal builds and tests are offline.

All 45 mapping records, lesson catalog, inventory CSV, and original verification
remain unchanged. Integrity tests allow only the requested approval metadata
changes and preserve every canonical Modedex, region, habitat, POI, zone, curation,
and artwork input. No spawn or quiz state depends on this overlay.

## Claim Boundary and Attribution

Educational lessons and representative algorithms are not evidence of a
Signature project's architecture, a particular organization's technology, or a
deployment at a gameplay coordinate. Canonical `signature.source_url` fields
remain separate and unchanged.

Preferred workbooks: [Explainable AI Workbook](https://explainableaiworkbook.com/),
[Data Science Workbook](https://datascienceworkbook.com/), and
[Deep Learning Workbook](https://deeplearningworkbook.com/), maintained by
Dr. Brinnae Bent. Outside references credit MIT News, IBM Think, and Optibus.
Consult publishers' attribution/license terms before reuse. We link to original
articles and store audit metadata, not lesson bodies. Project relevance judgments
do not imply publisher endorsement.
