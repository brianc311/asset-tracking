# Full Batch Scan (Quick / Full)

Date: 2026-11-21  
Status: draft for review

## Problem

Quick Batch Scan is the right tool for serial and MAC capture, but saved rows then show empty **Model** and **Location** on the assets list. Field work still needs the fast scan loop, plus a way to fill those two fields without leaving Batch Scan or opening New Asset.

## Decision

Keep a single **Batch Scan** page and session. Add a **Quick | Full** switch on the scan form.

- **Quick** stays serial, MAC 1, optional MAC 2, Skip 2nd MAC.
- **Full** adds Model and Location on the same form.
- Last Model and Location are remembered for the next save; serial and MACs still clear.
- No new models. Reuse `Asset.model_number` and `Asset.location`.

## User flow

1. Start a batch as today (site + device type).
2. On the scan page, choose **Quick** or **Full**. The choice is stored on the batch session and survives refresh.
3. **Quick:** scan serial and MAC 1, optionally MAC 2 or Skip 2nd MAC, Save Asset. Model and Location are hidden and stored blank.
4. **Full:** the Quick fields plus Model and Location. Both extra fields are optional. Save Asset writes them onto the asset.
5. After a successful Full save, the form comes back with serial and MACs empty, and Model/Location still filled with the last values. Change Location (Room1 → Room2) without retyping Model.
6. Switching back to Quick hides Model and Location. Quick saves still leave those fields blank on the new asset. Remembered Full values are kept for the next time Full is selected.
7. Batch Items shows Model and Location so missing values are visible without leaving the page.

## Session

Store on the current batch meta (`batch_sessions_meta` for the active key):

- `mode`: `"quick"` or `"full"` (default `"quick"`)
- `last_model_number`: last Model saved in Full (string, may be empty)
- `last_location`: last Location saved in Full (string, may be empty)

Switching modes updates `mode` immediately via GET `?mode=quick` or `?mode=full` on batch home, then redirects to `/scan/batch/` with no query string so a refresh stays in the chosen mode. Saving in Full updates `last_model_number` and `last_location` from that save. Saving in Quick does not change those remembered values.

On GET in Full, the item form is initialized with the remembered Model and Location. On GET in Quick, those fields are not shown. After a failed save, keep the posted values (including Model/Location) so the user can fix errors without losing typed data.

## Data

No schema change. Full save sets:

- `model_number` from the form
- `location` from the form

Quick save leaves both blank (`""`). Existing uniqueness, MAC normalize, barcode generation, timestamps, archive, report, and labels are unchanged.

## Validation

Unchanged from current Batch Scan:

- Serial and MAC 1 required
- MAC 2 optional (blank saves without Skip 2nd MAC; Skip still hides MAC 2)
- Duplicate serial at the same site rejected
- Duplicate MAC anywhere (as MAC 1 or MAC 2) rejected
- Invalid MAC format rejected
- MAC 2 must differ from MAC 1 when both are present

Model and Location are optional in Full. Errors render in red under the field.

## UI

- Quick | Full control at the top of the scan card, not a second nav item
- Full shows Model and Location under the MAC fields, same scan-button row pattern as serial/MAC (Scan on Model and Location is allowed; not required)
- Batch Items table columns: Select, #, Serial, MAC 1, MAC 2, Model, Location

## Out of scope

- Comments, photo, asset number, barcode type on Batch Scan
- A separate Full Batch Scan page
- Requiring Model or Location
- Changing site reports, PDF columns, or labels for model/location (assets list already shows them)
- Editing saved rows on this page (use asset Edit)

## Tests

- Full save with Model and Location stores both on the asset
- After Full save, GET batch home still shows those last Model and Location values
- Serial and MAC fields are empty after a successful save
- Quick save still works with blank Model and Location
- Quick save does not overwrite remembered last Model/Location
- GET `?mode=full` then GET `/scan/batch/` still renders Full fields
- Batch Items HTML includes Model and Location cells for a Full-saved row
- Failed duplicate save in Full redisplays posted Model and Location
