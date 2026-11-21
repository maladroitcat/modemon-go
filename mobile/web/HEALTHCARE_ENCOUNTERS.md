# Owner-approved Healthcare associations

On 2026-11-21 the owner approved Duke Department of Health, NC State Student
Health Center, and the Healthcare entries whose only exclusion was a missing
public-approach assessment, excluding both Hemp Farmacy records. This explicitly
extends the original engagement brief to twelve existing POIs. No new source
POIs, coordinates, habitats or species were created.

The exact instruction and decisions are in
[`config/healthcare_approvals.yaml`](config/healthcare_approvals.yaml). This
separate overlay preserves canonical POI tags, scores and historical curation.
These are owner-approved outdoor educational associations, not field-verified
sidewalk coordinates, permission to enter a facility, or evidence of deployed AI.

## Approved locations

| Stable POI ID | Location | Area |
| --- | --- | --- |
| `DUR-01_osm_node_13917907872` | Bull City Veterinary Hospital | Downtown Durham |
| `DUR-01_osm_node_14165026701` | Urban Tails Veterinary Hospital | Downtown Durham |
| `DUR-01_osm_node_1659112337` | Main Street Pharmacy | Downtown Durham |
| `DUR-01_osm_node_7674513212` | Walgreens | Downtown Durham |
| `DUR-02_osm_node_5808304716` | Duke Department of Health | Duke University |
| `RAL-01_osm_node_14232394214` | Gladwell Orthodontics | Downtown Raleigh |
| `RAL-01_osm_node_3248743365` | Downtown Dental | Downtown Raleigh |
| `RAL-01_osm_node_3305289269` | CVS Pharmacy | Downtown Raleigh |
| `RAL-01_osm_node_4533068539` | Glenwood South Pharmacy & Market | Downtown Raleigh |
| `RAL-01_osm_node_7967845007` | Person Street Pharmacy | Downtown Raleigh |
| `RAL-01_osm_way_47776939` | Oak Heart Veterinary Hospital | Downtown Raleigh |
| `RAL-03A_osm_way_47917752` | Student Health Center | NC State Central Campus |

Both Hemp Farmacy records (`RAL-01_osm_way_47663698` and
`RAL-01_osm_node_8412073792`) remain explicitly excluded. Other unapproved
clinical sites, Duke University Hospital and all WakeMed/RAL-05 locations stay
excluded. Duke Department of Health has a source OSM `fixme` questioning its
name/existence; its encounter retains an unverified-source notice. Student
Health Center's earlier rejection remains in analytical curation; this newer
approval applies only to an outdoor public association.

## Access and compatibility

Every approved encounter instructs players to use an open public sidewalk or
campus path, avoid healthcare buildings, treatment areas, private grounds and
patient-only spaces, keep entrances clear, and follow signs, hours and closures.
Real mode requires the existing public-approach acknowledgment plus unchanged
fresh GPS, accuracy and 75 m checks. Demo uses the same eligible locations,
explicit simulated movement and separate saved collection.

`scripts/healthcare_approvals.py` matches exact IDs, names and original exclusion
sets. It records previous exclusions/access notes, enables only approved POIs,
and stamps the approval version and effective date. Unknown IDs, duplicate or
excluded decisions, mismatched names, new access restrictions, adult/security
flags, and closed/unknown status fail the build. There is no global Healthcare
exemption.

The overlay takes effect on **2026-11-21**; earlier rotations remain identical.
From that date, additional candidates use the original deterministic ranking,
habitat matching, 70/30 rarity selection and seven-markers-per-half-mile density
rule. They can change which nearby candidates fit the cap. Existing POI/day
encounter IDs, species seeds, question banks and completed attempts retain
their identity. No attempts are deleted, reset or regraded.

The base gameplay fingerprint, `data_version`, compatibility alias and storage
keys are unchanged. Like Signature associations, this access overlay has its
own version and source hash included in runtime `source_hashes` and
`content_version`; the alias was not rewritten to conceal a new base world.

## Coverage result

Eligible anchors increase from **551 to 563**. All nine habitats are represented,
and all 51 species have eligible locations. The previous five-species gap and
eight blocked achievement conditions are resolved. Canonical badge requirements
are unchanged. The warning calculation remains and will still report genuine
missing-anchor requirements.

Eligibility does not promise a species on a particular day. Updated
[`coverage.json`](coverage.json) records 49 species in the 32-day sample from
2026-11-21 through 2026-12-22. Pathogaze and Clinink are unobserved in that sample;
**zero species lack eligible anchors**. A separate 128-day audit through
2027-03-28 confirms normal encounters for all five formerly unavailable species:

| Species | First observed in audit | Associated location |
| --- | --- | --- |
| Beatling | 2026-11-23 | Walgreens, Durham |
| Wardray | 2026-12-08 | Student Health Center, NC State |
| Wardwisp | 2026-12-14 | Urban Tails Veterinary Hospital |
| Pathogaze | 2027-01-10 | Glenwood South Pharmacy & Market |
| Clinink | 2027-02-04 | Urban Tails Veterinary Hospital |

These are deterministic audit examples. No encounters were forced, rarity
increased, or completed encounters reset to produce them.

## Validation

Python tests cover exact approvals, unchanged source data/coordinates, remaining
exclusions, provenance and access guards. Browser unit tests cover historical
worlds, encounter/question identity, all-five rotation coverage, determinism,
density, GPS limits and real/Demo parity. The original missing-anchor achievement
test remains with reconstructed pre-approval eligibility; current-world tests
verify no missing-anchor warnings.

New Chromium/WebKit cases capture all five species on normal Demo rotations,
reload saved progress, verify mastery and mode separation, and test Student
Health's real GPS and public-approach acknowledgment. Results are in
[the implementation report](ENGAGEMENT_PROGRESSION.md#validation-and-review-artifacts).

The [local preview](http://127.0.0.1:5173/) serves the update. No public deployment
or physical-device acceptance is implied.
