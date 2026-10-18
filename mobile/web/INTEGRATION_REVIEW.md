# Issue 23 integration review

## Repository consolidation

Base: current `origin/main` 984f31c. `dev/modemon_art` was identical to that base.
The branch `dev/issue-23-integration` preserves the pending generated-export
ignore rule and sequentially merges the existing approved stack, without squash,
rebase or cherry-pick duplication:

| Original PR | Integrated remote branch | Preserved merge tip |
| --- | --- | --- |
| 12 | already in main | 984f31c |
| 16 | dev/mobile-foundation | 7486a671 |
| 18 | dev/playable-web-mvp | 88c62d86 |
| 20 | dev/iphone-playtest-copy | 727370aa |
| 22 | dev/capture-quiz-difficulty | 5a4fd985 |

The sole merge conflict was the spelling of the generated `dist-*/` ignore rule;
the effective rule was retained. No gameplay source conflict occurred. An initial
octopus attempt stopped cleanly at that conflict; sequential merges preserved
all stack ancestors. No reset/clean, force push, original-art deletion or direct
main push is part of this workflow. The final PR targets main, not another stack.

## Scope and evidence

All 51 local creature masters and the logo are preserved and intentionally
tracked with responsive derivatives. See `assets/ARTWORK_README.md` and the
mapping report. Camera/Modedex use stable-ID images; maps remain anonymous.
The logo's yellow, navy and cyan palette informs the theme. Correct feedback
remains green and incorrect feedback red, with unchanged text and icons.

All twelve Signatures have real placement eligibility, not guaranteed daily
appearance. The deterministic schedule/version, daily escapes, all three quizzes,
75m GPS gate and global seven-in-half-mile cap remain. Shared anchors still
rotate one Signature at a time. Source research/links and canonical GIS/POI data
are unchanged from the approved gameplay tip d0388c0.

Cabcrab and Flowfin keep their curated association ID but use the public
Great Jones Street sidewalk beside agency-confirmed GoDurham stop 6680. This
avoids Durham Station construction and never falls back to its centroid. Hunt
uses the street-side Partners Way sidewalk; its October 19 building closure is
a dated linked notice, not an invented walkway closure. Other actual approach
closures still block. Full evidence and limitations are in
`SIGNATURE_ENCOUNTERS.md`. A separate mapped construction parcel across Great
Jones Street is not an approved player destination.

No approved Modedex, quiz, safety or UI copy is rewritten. The obsolete artwork
limitation is hidden only when all approved images exist. The station availability
sentence and new linked site notices are the authorized safety exceptions.

## Release gates

Automated Chromium and iPhone-sized WebKit checks are not physical iPhone Safari
acceptance. Before release, the owner must verify on an actual iPhone:

- Onboarding/logo, map scrolling and no horizontal overflow in portrait/landscape.
- Foreground GPS permission/accuracy, safe stopped approach and 75m interaction.
- User-gesture camera permission, transparent creature overlay, background/exit
  camera shutdown, denied-camera fallback and no uploaded frames.
- All three difficulty pickers, red/green feedback, capture/escape persistence
  after reload, and separate real/Demo records.
- Current public-path signage/closures at the chosen alternatives; mapping and
  official stop identity are desk evidence, not a field inspection.

Public preview deployment must identify its exact app commit and hosting version;
do not describe an old live preview as this integration. No automatic merge or
production acceptance is implied by the PR. The native Expo foundation is kept
and must continue passing its own checks and multi-platform export.
