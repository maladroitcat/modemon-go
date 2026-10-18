# Modedex Learning References: Research Only

Issue #26 / PR #29. No UI, canonical Modedex, quiz, artwork, geography, or
Signature project evidence is changed. No links are integrated, merged, or deployed.

## Final Owner Policy

- Preserve **all 45 existing workbook matches unchanged**, including accepted
  component-level matches and existing Signature workbook matches.
- All **12 Signature Modemon already have sufficient canonical real-world project
  links**. Do not research or propose supplementary sources for them.
- Research only the **four uncovered non-Signatures**: Wardray, Routeopus,
  Shiftshark, and Parcelprawn.
- Outside proposals must explain what this kind of AI does and where it is used
  for an everyday reader, not teach implementation.
- **Every outside reference is PENDING_OWNER_APPROVAL**, including verified URLs.
  No desire for 51 supplementary links overrides this policy.

## Scope Accounting

The original 40-match inventory had 11 blank workbook fields: three Signatures
(Specimunk, Flowfin, Cabcrab) and eight non-Signatures (Scribbit, Clinink,
Bureaucritter, Manusqueak, Wardray, Routeopus, Shiftshark, Parcelprawn).

The existing PR now has 45 matches, which the owner accepts as-is. Scribbit,
Clinink, Bureaucritter, Manusqueak, and Flowfin gained scoped workbook matches in
that earlier review. Those matches are not reverted or reassessed.

Of the current six blank workbook fields, two belong to Signatures (Specimunk,
Cabcrab) and need no extra links. Only the other four require outside research.
Thus **35 of 39 non-Signatures have workbook matches**, four have pending outside
proposals, and **12 of 12 Signatures have canonical project provenance**.
The machine-readable [scope audit](research/modedex_reference_scope.json)
derives this accounting from canonical stages and historical review metadata.

## Review Artifacts

- [Table A](research/modedex_learning_mapping.md) preserves all 45 existing
  matches, exact URLs, rationales, component scope labels, and optional secondary
  lessons. Null workbook fields are never filled with outside proposals.
- [Workbook YAML](config/modedex_learning_links.yaml),
  [51-row inventory](research/modedex_learning_inventory.csv), and
  [workbook verification](research/workbook_lesson_verification.json) remain
  byte-for-byte unchanged by this final clarification.
- [Table B](research/modedex_external_owner_review.md) and its
  [CSV](research/modedex_external_owner_review.csv) contain four proposals with
  title, publisher, exact URL, rationale, audience suitability, confidence,
  limitations, and why the workbook review did not cover that job.
- [Editable outside proposals](research/modedex_external_proposals.yaml) are
  research metadata only, not an approved application link catalog.
- [Outside verification](research/external_reference_verification.json) records
  HTTP status, exact observed title, URL, inspected topic terms, response hash,
  and verification time. Working links do not constitute owner approval.

### Proposed Reading

| Species | Publisher / exact article | Purpose |
|---|---|---|
| Wardray | MIT News: [Robot helps nurses schedule tasks on labor floor](https://news.mit.edu/2016/robot-helps-nurses-schedule-tasks-on-labor-floor-0713) | Familiar hospital examples show AI suggesting nurse assignments and patient room moves. |
| Routeopus | MIT News: [Software that knows the risks](https://news.mit.edu/2015/planning-algorithms-evaluate-probability-of-success-0115) | Everyday travel and bus examples explain scheduling under uncertain journey times. |
| Shiftshark | IBM Think: [What is contact center workforce optimization?](https://www.ibm.com/think/topics/contact-center-workforce-optimization) | Explains matching staff, skills, availability, and demand to schedules. |
| Parcelprawn | IBM Think: [What is dispatch management?](https://www.ibm.com/think/topics/dispatch-management) | Explains coordinating delivery assignments and routes, including AI assistance and human oversight. |

**All four are PENDING_OWNER_APPROVAL.** The MIT articles are dated research
examples, not evidence of current production deployment. Routeopus's later
graph/probability discussion is more technical than its accessible opening.
IBM's articles are vendor-authored and broader than scheduling alone.
Not all automation or optimization is machine learning, and no source establishes
local deployment, safe clinical practice, equitable staffing, or guaranteed results.
These limitations are explicit per proposal rather than silently overstated.

## Preserved Historical Research

The prior review inspected the public discovered corpus of 360 lessons across
15 unit TOCs (123 Explainable AI, 121 Data Science, 116 Deep Learning).
[TOC inventory](research/workbook_toc_inventory.json) and
[body-audit metadata](research/workbook_full_review.json) remain unchanged.
The [21-species component review](research/workbook_component_review.yaml) and
[21-row review queue](research/modedex_learning_review_queue.csv) are **historical**,
not instructions to revisit accepted workbook matches or research Signatures.
Their old confidence/review flags are retained for provenance, not a new approval
request. Search terms alone were never proof of topic relevance.

The former code-oriented outside proposals and supplementary Signature proposals
have been withdrawn from the current Table B and verification evidence. Their
history remains in Git. No new Signature sources were researched for this revision.

## Claim Boundary

Canonical `signature.source_url` values remain separate and unchanged.
Existing project links already satisfy all 12 Signatures. Educational readings
do not identify a project's deployed architecture, prove current local usage,
or imply that a system runs at a gameplay coordinate. No canonical algorithm
list or research fact is altered by a proposed reading.

## Reproduction and Checks

With the existing Python requirements installed, from the repository root:

```sh
# Offline bookkeeping only: preserves all existing workbook match values.
python3 -B -m scripts.build_workbook_research_review
# Explicit live audit of ONLY the four pending non-Signature outside sources:
python3 -B -m scripts.review_external_learning_references --verify
# Deterministic offline Table B and scope-audit rendering:
python3 -B -m scripts.review_external_learning_references
python3 -B -m unittest discover -s tests -v
```

No PDF package is needed. Historical workbook-crawl helpers are retained for
provenance; rerunning or revising preferred matches is not part of this task.
The HTML audit checks article content rather than navigation; unexpected redirects,
title changes, missing terms, or stale/out-of-scope evidence fail validation.
Tests are offline. Snapshots cannot guarantee future public availability.

SHA-256 tests freeze the workbook YAML, inventory CSV, and workbook verification
snapshot. The protected-source manifest checks all pre-existing configuration and
processed datasets; renderers verify before/after hashes. Tests also enforce
non-Signature-only proposals, general-audience resource types, deterministic
reports, pending-only status, and absence of proposed URLs from the game/canon.

## Owner Decisions Needed

Approve or reject each of the four Table B species/reference pairs, or request
different plain-language sources. No further workbook reassessment or Signature
supplement is requested. A later explicitly authorized task would be required
to integrate approved readings into the app. This research has no approval,
integration, merge, or deployment command.

## Attribution

Preferred workbooks: [Explainable AI Workbook](https://explainableaiworkbook.com/),
[Data Science Workbook](https://datascienceworkbook.com/), and
[Deep Learning Workbook](https://deeplearningworkbook.com/), maintained by
Dr. Brinnae Bent. Pending outside references credit MIT News / Massachusetts
Institute of Technology and IBM Think individually. Consult original publishers'
attribution and licensing terms before reuse. We link to originals and retain
audit metadata, not article bodies. Project relevance judgments do not imply
publisher endorsement.
