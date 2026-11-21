# Device Name and report column picker

Date: 2026-11-21  
Status: draft for review

## Problem

Assets are labeled with hostnames such as `EPS-Switch-01` or `EPS-AP-01`. Location is the room/spot, not that name, so the assets list and site report cannot show what was printed on the label. Reports also always show every column; sometimes a shorter print is enough.

## Decision

1. Add optional **Device Name** on `Asset`.
2. Collect it on New Asset, asset edit, Quick Batch Scan, and Full Batch Scan.
3. Show it on the assets list, asset detail, Batch Items, and site/print reports (HTML and PDF).
4. Add a **Columns** picker on site/print reports only. Default is all fields. Choices live in the URL so Print and Download PDF match.

No new models. Batch Scan report stays as-is (no column picker). Emailed site-report PDF includes Device Name as a normal extra column and has no picker.

## Data

Add `Asset.device_name`: `CharField(max_length=128, blank=True)`. Not unique. Optional. Empty string for existing rows.

Place it after Product in display order:

`# | Barcode | Site | Product | Device Name | Serial | MAC | MAC 2 | Model | Location | Comments`

On create/edit forms, put Device Name after Product and before Serial.

## User flow — capture

- **New Asset / Edit:** optional Device Name text field (placeholder `EPS-Switch-01`).
- **Quick Batch Scan:** Serial, MAC 1, MAC 2 / Skip, **Device Name**.
- **Full Batch Scan:** those fields plus Model and Location.
- Device Name is optional. Invalid or duplicate serial/MAC rules are unchanged.
- After a successful batch save (Quick or Full), serial and MACs clear. Device Name stays filled from `last_device_name`. Full still also keeps last Model and Location.
- Quick saves still leave Model and Location blank and do not overwrite those remembered Full values. Quick **does** save Device Name and updates `last_device_name`.
- Batch Items shows a Device Name column.
- Assets list search matches Device Name (`icontains`).

## Session

On batch meta, add:

- `last_device_name`: string, may be empty

Set it after every successful batch save from the posted Device Name (Quick or Full). GET form initial includes `device_name` from this value in both Quick and Full. Failed save keeps the bound form (posted Device Name stays).

## Reports — site / print

Applies to `/assets/reports/view/` (site report) and `/assets/report/` (print report), including `export=pdf`.

Column keys and labels:

| key | label |
|-----|--------|
| `number` | # |
| `barcode` | Barcode |
| `site` | Site |
| `product` | Product |
| `device_name` | Device Name |
| `serial` | Serial |
| `mac` | MAC |
| `mac_2` | MAC 2 |
| `model` | Model |
| `location` | Location |
| `comments` | Comments |

Default when `cols` is missing or empty: all keys, in that order.

`cols` is a comma-separated list of keys. Unknown keys are ignored. Duplicate keys are ignored. Order on the report follows the table above (not the order the boxes were checked). If every key is stripped as unknown, fall back to all fields.

**MAC 2:** if `mac_2` is selected but no row has `mac_address_2`, omit the column (same as today). If `mac_2` is not selected, omit it even when values exist.

UI: a **Columns** row of checkboxes above the table (no-print so they do not appear on paper). Checking or unchecking reloads the same report URL with the updated `cols` query, preserving `site`, `ids`, and `session`. The Download PDF link includes the same `cols`.

`assets_pdf_bytes` / `asset_report_table_data` take the selected keys and only emit those columns. Email PDF calls the same builder with the default (all) keys, plus Device Name.

## Out of scope

- Column picker on Batch Scan report or emailed PDF
- Device Name on labels
- Requiring or uniquifying Device Name
- Auto-incrementing `EPS-Switch-01` → `02`

## Tests

- Create/edit saves `device_name`
- Quick batch save stores Device Name and remembers it on the next GET
- Full batch save stores Device Name, Model, and Location
- Assets list shows Device Name and search finds it
- Site/print HTML includes Device Name when `cols` omitted
- `cols=serial,mac` omits Device Name (and other unselected columns)
- PDF uses the same selected columns
- Selected `mac_2` still omitted when every row’s MAC 2 is empty
