# Approved game artwork

Issue 23 authorizes the owner's 51 local creature images and Modemon GO logo.
`artwork_sources.json` records the exact root filename, canonical stable ID,
tracked master path and SHA-256. The root drops remain untouched. The earlier
Seeklet concept iterations are not used or approved by this integration.

## Reproduce

```sh
python3 -B scripts/build_game_art.py
python3 -B scripts/build_web_runtime.py
```

Install `requirements.txt` first. A fresh checkout uses committed masters, not
the untracked root drops. `--import-local` is the one-time import option: it
requires exactly one named image per canonical creature and the logo, rejects
unknown/missing/duplicate matches, and never overwrites a differing master.

Full-resolution PNGs live in `modemon/approved/originals/` and
`brand/originals/`. They are byte-for-byte copies, not recompressed sources.
The runtime does not serve these masters. No artwork was generated, recolored,
redesigned or given an AI-created background.

## Derivatives and loading

Only fully transparent exterior pixels are trimmed. The complete creature is
aspect-fitted with 3% transparent padding per edge; silhouettes are not cropped.
WebP derivatives are 96, 320 and 640 pixels square, with a 320px PNG fallback.
The logo keeps its original 2:1 aspect ratio. Alpha is retained. Derivatives strip
source metadata; masters do not. Pillow 10.3.0 and WebP 1.3.2 produced this set;
encoder upgrades may change derivative bytes, never the master hashes.

`mobile/web/src/data/art.json` maps stable IDs to content-hashed URLs and file
hashes/dimensions. `mobile/web/public/art/` contains 208 derivatives: 51 creatures
and one logo, four formats/sizes each. Total size is 10,827,827 bytes. Median
96/320/640 WebP sizes are about 6/27/69 KB; maximum WebP is 124,136 bytes.
The 320px PNG median is about 108 KB, maximum 169,632 bytes. Tests enforce
130 KB per WebP, 220 KB per PNG and 12 MB for the entire derivative set.

`<picture>` selects responsive WebP with lazy loading and asynchronous decoding.
An image failure retries PNG, then shows the pre-existing explicit unavailable
placeholder. The logo has eager priority and accessible heading text; it falls
back to that text. Anonymous map markers never request creature artwork. Camera
and no-camera encounters use the same images and do not record/upload frames.

## Audit

`output/artwork_mapping_report.json` lists all matches, hashes, sizes and alpha
bounds. `output/artwork_contact_sheet.jpg` is an inspection sheet of existing art,
not new creative content. All 51 canonical IDs match; none is missing, ambiguous
or duplicated. Artwork provenance/ownership remains the owner's supplied art;
this implementation does not invent a license grant for the images.
