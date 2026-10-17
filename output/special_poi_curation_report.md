# Special POI human-curation audit

Verification date: 2026-10-17. Decisions supplied by the project team; no new web verification or scoring.

## Primary

- DUR-01 #1 Hayti Heritage Center: Strong educational destination with richer and less generic context than many downtown entertainment POIs.
- DUR-01 #2 Museum of Durham History: Free, public-facing local-history institution with strong educational context.
- DUR-01 #3 Durham Station: Excellent Transportation context for forecasting, scheduling, routing, optimization, anomaly detection, and demand modeling. Retain as a conditional primary.
- DUR-02 #1 Nasher Museum of Art: Strong visual, classification, recommendation, language, and interpretability educational contexts.
- DUR-02 #2 Perkins Library: Strong search, information retrieval, NLP, recommendation, and knowledge-system context.
- DUR-02 #3 Jack Katz Stadium: Distinct sports-AI educational context including tracking, computer vision, forecasting, optimization, classification, and performance analytics.
- RAL-01 #1 North Carolina Museum of Natural Sciences: Exceptionally rich scientific and educational AI/ML contexts without asserting exact-location deployment.
- RAL-01 #2 Raleigh Union Station Bus Facility: Distinct Transportation context for forecasting, routing, scheduling, optimization, anomaly detection, classification, and demand modeling.
- RAL-01 #3 Artspace: Strong computer vision, classification, recommendation, generative-AI, creativity, and human-versus-machine interpretation contexts.
- RAL-02 #1 Big Field: Flexible public park destination suitable for gameplay association.
- RAL-02 #2 Gipson Play Plaza: Highly public and distinctive destination when the overall plaza is the association anchor, not a children's play structure.
- RAL-03A #1 NC State Crafts Center: Rich art, fabrication, visual-model, and human-creativity educational contexts.
- RAL-03A #2 SOL Garden: Broadens campus ecology beyond buildings with environmental, forecasting, classification, vision, and optimization contexts.
- RAL-03B #1 Pullen Park Amusement Center: Recognizable public-facing recreation destination; temporary nearby construction is not enough to remove it.
- RAL-03B #2 Theater In The Park: Different educational context from the amusement area.
- RAL-04 #1 James B. Hunt Jr. Library: Strong search, NLP, retrieval, recommendation, automation, and information-system contexts in an engaging technological environment.
- RAL-04 #2 William and Ida Friday Institute for Educational Innovation: Exceptionally strong AI-education context, without asserting deployment of a particular model at the player coordinate.

## Alternate

- DUR-01 #1 Durham Performing Arts Center: Strong public cultural/event fallback.
- DUR-01 #2 Durham County Library - Main Library: Reliable public fallback, though less distinctive than the selected primary set.
- DUR-01 #3 Historic Durham Athletic Park: Athletic destination retained as an event-access-dependent fallback.
- DUR-02 #1 R.J. Reynolds Industries Theater: Useful alternative arts and event environment.
- DUR-02 #2 Wallace Wade Stadium: Less consistently suitable than Jack Katz Stadium; retain as a conditional fallback.
- RAL-01 #1 Marbles Kids Museum: Useful fallback; the three primary locations provide greater ecological variety.
- RAL-01 #2 Betty Ray McCain Art Gallery: Retain as a conditional cultural fallback.
- RAL-02 #1 Sunflower Field: Strong public fallback with seasonal limitations.
- RAL-03A #1 Price Music Center: Retain as a conditional performing-arts alternative.
- RAL-03B #1 Pullen Community Center: Reliable public fallback destination.
- RAL-04 #1 Venture Courtyard: Useful fallback association anchor.
- RAL-04 #2 NC Japan Center: Useful conditional cultural and educational alternative.

## Deferred

- DUR-02 Lilly Library: Re-evaluate in a future data refresh; do not delete the underlying POI.

## Not Selected

- RAL-01 Finch Library: Better downtown candidates have clearer public-facing access; this is not a closed or sensitive designation.
- RAL-03A Weisiger Brown Athletic Facility: Not sufficiently public-facing as a visitor destination compared with the selected campus locations.

## Rejected

- DUR-01 LGBTQ Center of Durham: Do not encourage unrelated players to linger at sensitive services. Retain the ordinary contextual POI unchanged.
- DUR-01 Shodor: Closed organization is not a viable special destination.
- DUR-02 Duke University Hospital: Excellent ordinary Healthcare habitat, but inappropriate as a deliberate special-gameplay destination.
- DUR-02 Putman quad: Insufficient evidence for a special destination; retain the canonical OSM-derived POI unchanged.
- RAL-01 Express Library Fayetteville Street: Remains a valid library/context POI, but should not be promoted as a special game-lingering destination.
- RAL-01 RUMAH: Mutual-aid/resource-distribution context and location instability make a poor special gameplay anchor; keep the underlying POI.
- RAL-02 NC Department of Health and Human Services Social Services: Reject the stale anchor; do not redirect the old POI to a new address or modify its coordinates.
- RAL-03A Student Health Center: Keep as Healthcare context, not as a deliberate special gameplay destination.
- RAL-04 The Cistern: Not distinctive or important enough to justify uncertainty; do not delete the canonical OSM-derived POI.
- RAL-05 WakeMed Health & Hospitals: Raleigh Campus: Excellent ordinary Healthcare habitat but inappropriate for intentional special-gameplay traffic. RAL-05 intentionally has zero primary destinations; do not force one.

## Current-status anomalies

- DUR-01 The History Hub Museum -> Museum of Durham History (relocated_renamed): The organization and venue are currently known as the Museum of Durham History; The History Hub is a stale mapped name.
- DUR-01 Durham Station -> Durham Station (temporarily_impacted): Active GoDurham bus transit center at 515 W. Pettigrew Street, not the nearby Amtrak station; undergoing substantial renovation in October 2026.
- DUR-01 Shodor -> Shodor (closed): Shodor officially ceased operations on June 30, 2024.
- DUR-02 Lilly Library -> Lilly Library (temporarily_impacted): Main building closed for renovation until Spring 2027; temporary operations were also disrupted in September 2026.
- DUR-02 Putman quad -> Putman quad (unknown): Mapped identity could not be independently corroborated strongly enough.
- RAL-02 NC Department of Health and Human Services Social Services -> NC Department of Health and Human Services Social Services (relocated_renamed): Mapped Boylan Avenue location is stale for the current Division of Social Services physical address.
- RAL-03B Pullen Park Amusement Center -> Pullen Park Amusement Center (temporarily_impacted): Lake Howell shoreline work affects some surrounding paths in October 2026, but major Pullen attractions remain operational.
- RAL-04 The Cistern -> The Cistern (unknown): Third-party mapping contains the feature, but a convincing current first-party NC State identity could not be established.

## Display-name overrides (source names retained)

- DUR-01 St. Joseph's Historic Foundation Hayti Heritage Center -> Hayti Heritage Center (active): Active cultural, historical, arts, and community institution.
- DUR-01 The History Hub Museum -> Museum of Durham History (relocated_renamed): The organization and venue are currently known as the Museum of Durham History; The History Hub is a stale mapped name.
- DUR-01 Durham Athletic Park -> Historic Durham Athletic Park (active): City-owned active facility, but interior access may depend on events.

## Sensitive/not recommended

- DUR-01 LGBTQ Center of Durham -> LGBTQ Center of Durham (active): Provides sensitive community services including support programming and resource services.
- DUR-02 Duke University Hospital -> Duke University Hospital (active): Acute-care, patient, emergency, and restricted clinical contexts.
- RAL-01 Express Library Fayetteville Street -> Express Library Fayetteville Street (active): Branch intentionally serves people navigating court matters, housing insecurity, homelessness, and related support needs.
- RAL-01 RUMAH -> RUMAH (active): Active organization announced a move to a new location in late 2026.
- RAL-03A Student Health Center -> Student Health Center (active): Student medical and mental-health clinical environment.
- RAL-05 WakeMed Health & Hospitals: Raleigh Campus -> WakeMed Health & Hospitals: Raleigh Campus (active): Active visitor-accessible major acute-care hospital with emergency, pediatric, patient, and clinical environments.

## Conditional primaries

- DUR-01 Durham Station -> Durham Station (temporarily_impacted): Active GoDurham bus transit center at 515 W. Pettigrew Street, not the nearby Amtrak station; undergoing substantial renovation in October 2026.
- RAL-02 Gipson Play Plaza -> Gipson Play Plaza (active): Active public destination, conditional on associating gameplay with the broader plaza/garden/common-space environment rather than children's play equipment.
  Anchor limitation: Associate gameplay with the broader public plaza/garden/common-space environment. Do not instruct players to approach, occupy, or linger around individual children's play equipment.
- RAL-03B Pullen Park Amusement Center -> Pullen Park Amusement Center (temporarily_impacted): Lake Howell shoreline work affects some surrounding paths in October 2026, but major Pullen attractions remain operational.

## Coverage and integrity

- RAL-02: 2 primary destinations; fewer than three is intentional.
- RAL-03A: 2 primary destinations; fewer than three is intentional.
- RAL-03B: 2 primary destinations; fewer than three is intentional.
- RAL-04: 2 primary destinations; fewer than three is intentional.
- RAL-05: 0 primary destinations; fewer than three is intentional.

RAL-05 intentionally has zero primaries. WakeMed remains an ordinary Healthcare POI, not a special-gameplay destination.

All 188 protected files hashed before/after; no changes. All original shortlist fields preserved exactly.
Automated curation validation passed. Run the complete unit suite with `python3 -B -m unittest discover -s tests -v`.

Primary means an approved destination, not a currently active spawn. No timing, rarity, geofencing, or model-family assignments are defined.
