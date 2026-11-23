# Device labels: Device Name and extra field picker

Date: 2026-11-21  
Status: approved

## Problem

Device labels print type, site, serial, and MACs. Install stickers need the hostname (**Device Name**) as the main line, plus a couple of extra fields the user picks at print time.

## Decision

On **Print device labels** only:

1. Main line is Device Name when filled; otherwise there is no unlabeled main line.
2. Extra text lines come from a checkbox picker on the label preview page. Default extras: Serial, MAC, MAC 2. Serial is always labeled `Serial: …` when selected, even if Device Name is blank.
3. Serial / MAC / MAC 2 barcodes stay on the sticker whether or not their text is checked.
4. Empty extra fields are omitted.
5. **Value labels** are unchanged. No picker on Batch Scan home. No new models.

## Extra field keys

`serial`, `mac`, `mac_2`, `model`, `location`, `barcode`

Query: `?mode=device&fields=serial,mac,location` (and existing `ids=`). Missing `fields` uses the default. Empty `fields=` means Device Name (or Serial fallback) only.

## Sticker

- Title: `{product} — {site}`
- Main: Device Name when filled
- Extras: `Label: value` one line each, picker order (Serial is labeled even when Device Name is blank)
- Barcodes: serial, MAC, MAC 2 when those values exist
