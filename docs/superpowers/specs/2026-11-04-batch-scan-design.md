# Batch Scan page

Date: 2026-11-04  
Status: draft for review

## Problem

The existing asset form and scan flow collect more fields than needed for a site install (product, model, location, photo). Field work needs a faster page: choose a site, scan a batch of one device type (all APs, then all switches), capture serial + MAC + optional second MAC, timestamp it, then archive, print a report, or print labels.

## Decision

Add a **Batch Scan** page on top of the existing `Asset` model. Do not create a separate intake table. Current Assets list, scan page, and site reports stay as they are.

## User flow

1. Open **Batch Scan** from the main nav (Staff+ who can manage assets).
2. Choose or create a **site**.
3. Choose or type a **device type** (examples: AP, Switch). Known types come from existing `product_name` values, same pattern as site names. Type stays set for the batch.
4. Scan **serial**, **MAC 1**, and **MAC 2**.
5. Check **Skip 2nd MAC** when the device has only one MAC. That hides MAC 2 and does not require it.
6. Save. The row is timestamped (`created_at`) and appears in the session list and in the normal Assets list.
7. Repeat. Change type (same site) to start the next batch (switches after APs).
8. Select one or many rows to **archive**, **print report**, or **print labels**.

## Data

Add two fields on `Asset`:

- `mac_address` — CharField, blank allowed for older assets; required on Batch Scan
- `mac_address_2` — CharField, blank allowed; required on Batch Scan unless Skip 2nd MAC is checked

Reuse existing fields:

- `site_name`
- `product_name` for device type (AP, Switch, or typed value)
- `serial_number`
- `created_at` as the timestamp
- `is_archived` / `archived_at`

No new Site or Batch models. Session remembers the current site and type the same way today’s scan session remembers site.

## Validation

- Site and device type are required before the first save.
- Serial and MAC 1 are required.
- MAC 2 is required unless **Skip 2nd MAC** is checked. If checked, store MAC 2 as blank.
- Normalize MACs to uppercase colon form (`AA:BB:CC:DD:EE:FF`). Accept typed or scanned `AA-BB-CC-DD-EE-FF` or 12 hex digits.
- Reject invalid MAC format.
- Reject if MAC 2 equals MAC 1.
- **No duplicates and no override:**
  - Serial must be unique among **non-archived** assets at the **same site**.
  - MAC 1 and MAC 2 must be unique among **non-archived** assets **everywhere** (a MAC cannot appear as either MAC field on another active asset).
- On duplicate, show an error and do not save. There is no “save anyway” confirm.

## Archive

Reuse the existing bulk archive action. On Batch Scan, selected rows can be archived (one or many). Archived rows drop out of the active batch list and site reports. Same permission rules as today’s asset archive.

## Report

A Batch Scan report for the current site (optionally filtered by the current type):

- Site, type, serial, MAC 1, MAC 2 (or “—” if skipped), timestamp
- A barcode image for the serial
- A barcode image for MAC 1
- A barcode image for MAC 2 when present

Print via the browser and PDF download, matching existing site report patterns. Use Code 128 for serial and MAC values (they are alphanumeric / hex). Existing asset barcode (`barcode_value`) is unchanged and is not the report barcode for these fields.

## Labels

When printing labels, the user chooses one mode:

1. **Device** — one sticker per selected asset: site, type, serial, MAC(s), and barcodes for serial + each MAC.
2. **Per value** — one sticker per value: serial, MAC 1, and MAC 2 if present.

Print selected rows only. If none are selected, print the current active batch (current site, current type, not archived).

## Out of scope

- Replacing `/scan/` or the existing asset create/edit form
- Emailing this report (existing site-report email stays as-is)
- Photos, model, location, or comments on the Batch Scan form
- Unique serials across different sites
- Editing MAC fields on this page after save (use existing asset edit)

## Tests

- Skip 2nd MAC saves with blank `mac_address_2`
- Unchecked Skip 2nd MAC rejects a missing MAC 2
- Duplicate serial at the same site is rejected
- Duplicate serial at a different site is allowed
- Duplicate MAC (as MAC 1 or MAC 2, any site) is rejected
- Report includes barcodes for serial and each present MAC
- Label mode “device” emits one label per asset
- Label mode “per value” emits one label per serial/MAC

## Navigation

Add **Batch Scan** next to **Scan** in the main nav for users who can manage assets.
