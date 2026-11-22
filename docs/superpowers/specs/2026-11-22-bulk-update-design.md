# Bulk update selected assets

Date: 2026-11-22  
Status: approved

## Problem

Staff can only bulk archive or delete. Correcting Product (or Site/Model/Location) for many assets at one site means editing each row.

## Decision

On the Assets list, **Update selected** applies **one field and one value** to the checked rows.

Editable: Product, Site, Model, Location, Comments.  
Not editable: Serial, MAC, MAC 2, Device Name, barcode, photo, asset number.

Archive and Delete stay as they are. Same permission as Edit (`can_manage_assets`). Confirm before apply.

## Flow

1. Filter/search (optional), check rows.
2. Update selected → choose field → enter value (Product/Site use existing dropdowns including “add new”).
3. Confirm: “Set Product to Switches on 12 items?”
4. POST `/assets/bulk/` with `action=update`. Success message. Empty Model/Location/Comments clears those fields. Product is required. Site is required (pick existing or add new).
