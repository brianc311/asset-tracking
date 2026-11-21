# Device Name and Report Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional Device Name on assets (including Quick and Full Batch Scan) and a default-all column picker on site/print reports.

**Architecture:** New `Asset.device_name` field plus `apps/assets/report_columns.py` to parse `cols=` and decide visible headers. Capture Device Name on AssetForm and BatchItemForm. Remember `last_device_name` on the batch session. Site/print HTML and PDF read the same selected keys.

**Tech Stack:** Django 5, existing Batch Scan session, ReportLab PDFs, Django `TestCase` via `manage.py test`.

## Global Constraints

- Optional `Asset.device_name` CharField max_length 128, blank, not unique.
- Display order after Product: `# | Barcode | Site | Product | Device Name | Serial | MAC | MAC 2 | Model | Location | Comments`.
- Collect Device Name on New Asset, edit, Quick Batch Scan, and Full Batch Scan.
- After batch save, serial and MACs clear; Device Name is remembered (`last_device_name`) in Quick and Full.
- Quick still leaves Model/Location blank and does not overwrite those remembered Full values.
- Column picker only on site/print HTML and PDF. Default all fields when `cols` is missing or empty.
- `cols` is comma-separated keys; unknown/duplicate keys ignored; if none remain, fall back to all. Report order follows the key table, not checkbox order.
- If `mac_2` is selected but no row has MAC 2, omit that column. If unselected, omit even when values exist.
- No picker on Batch Scan report or emailed PDF. Email PDF uses default (all) columns including Device Name.
- Do not add Device Name to labels. Do not require or uniquify Device Name. Do not auto-increment names.
- Run tests with: `.\.venv\Scripts\python.exe manage.py test <dotted.path> -v 2`

## File map

- Create: `apps/assets/migrations/0005_asset_device_name.py`
- Create: `apps/assets/report_columns.py`
- Create: `apps/assets/tests/test_report_columns.py`
- Modify: `apps/assets/models.py`
- Modify: `apps/assets/forms.py`
- Modify: `apps/assets/views.py`
- Modify: `apps/assets/barcode_utils.py`
- Modify: `templates/assets/list.html`
- Modify: `templates/assets/detail.html`
- Modify: `templates/assets/print_report.html`
- Modify: `templates/assets/site_report.html`
- Modify: `apps/scan/forms.py`
- Modify: `apps/scan/batch.py`
- Modify: `templates/scan/batch_home.html`
- Modify: `apps/assets/tests/test_asset_create.py`
- Modify: `apps/assets/tests/test_asset_reports.py`
- Modify: `apps/scan/tests/test_batch_scan.py`

---

### Task 1: Device Name field and migration

**Files:**
- Modify: `apps/assets/models.py`
- Create: `apps/assets/migrations/0005_asset_device_name.py`
- Test: `apps/assets/tests/test_asset_create.py`

**Interfaces:**
- Consumes: existing `Asset` model
- Produces: `Asset.device_name` — `CharField(max_length=128, blank=True)`, default `""`

- [ ] **Step 1: Write the failing test**

Add to `apps/assets/tests/test_asset_create.py`:

```python
class AssetDeviceNameTests(TestCase):
    def test_device_name_defaults_blank(self):
        asset = Asset.objects.create(
            product_name="Switches",
            barcode_value="AT-DEVNAME01",
        )
        self.assertEqual(asset.device_name, "")

    def test_device_name_persists(self):
        asset = Asset.objects.create(
            product_name="Switches",
            barcode_value="AT-DEVNAME02",
            device_name="EPS-Switch-01",
        )
        asset.refresh_from_db()
        self.assertEqual(asset.device_name, "EPS-Switch-01")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_asset_create.AssetDeviceNameTests -v 2`

Expected: FAIL — `Asset` has no `device_name`

- [ ] **Step 3: Write minimal implementation**

On `Asset` in `apps/assets/models.py`, add after `product_name`:

```python
    device_name = models.CharField(max_length=128, blank=True)
```

Create `apps/assets/migrations/0005_asset_device_name.py`:

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0004_asset_mac_addresses"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="device_name",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_asset_create.AssetDeviceNameTests -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/assets/models.py apps/assets/migrations/0005_asset_device_name.py apps/assets/tests/test_asset_create.py
git commit -m "Add optional device name on assets for labeled hostnames."
```

---

### Task 2: Create, edit, list, detail, and search

**Files:**
- Modify: `apps/assets/forms.py`
- Modify: `apps/assets/views.py` (search `Q` in `asset_list`)
- Modify: `templates/assets/list.html`
- Modify: `templates/assets/detail.html`
- Test: `apps/assets/tests/test_asset_create.py`

**Interfaces:**
- Consumes: `Asset.device_name`
- Produces: AssetForm field `device_name` after `product_name` (placeholder `EPS-Switch-01`). List column after Product. Detail line after Product. Search includes `device_name__icontains`.

- [ ] **Step 1: Write the failing test**

Add to `AssetDeviceNameTests` in `apps/assets/tests/test_asset_create.py`:

```python
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)

    def test_create_saves_device_name(self):
        response = self.client.post(
            "/assets/new/",
            {
                "site_name": NEW_SITE_VALUE,
                "new_site_name": "Test",
                "product_name": "Switches",
                "device_name": "EPS-Switch-01",
                "serial_number": "444444",
                "mac_address": "1A-23-7G-4E-12-9A",
                "location": "Room1",
                "barcode_type": "qr",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        asset = Asset.objects.get(serial_number="444444")
        self.assertEqual(asset.device_name, "EPS-Switch-01")

    def test_list_shows_and_searches_device_name(self):
        Asset.objects.create(
            site_name="Test",
            product_name="Switches",
            device_name="EPS-Switch-01",
            serial_number="SN-LIST",
            barcode_value="AT-DEVLIST01",
        )
        listed = self.client.get("/assets/")
        self.assertContains(listed, "<th>Device Name</th>")
        self.assertContains(listed, "EPS-Switch-01")
        found = self.client.get("/assets/", {"q": "EPS-Switch-01"})
        self.assertContains(found, "SN-LIST")
        missed = self.client.get("/assets/", {"q": "no-such-name"})
        self.assertNotContains(missed, "SN-LIST")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_asset_create.AssetDeviceNameTests -v 2`

Expected: FAIL — create POST does not persist `device_name` (field not on form)

- [ ] **Step 3: Write minimal implementation**

In `apps/assets/forms.py`, insert `"device_name"` in `ASSET_FIELD_ORDER` immediately after `"product_name"`, add `"device_name"` to `Meta.fields` in the same place, and add widget:

```python
            "device_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "EPS-Switch-01"}
            ),
```

Set `self.fields["device_name"].required = False` in `__init__` (blank model field already optional).

In `apps/assets/views.py` `asset_list` search filters, add:

```python
            | Q(device_name__icontains=q)
```

In `templates/assets/list.html` thead, add `<th>Device Name</th>` after Product. In the row, after the product `<td>`, add:

```html
          <td>{{ asset.device_name|default:"—" }}</td>
```

Increase the empty-row `colspan` by 1 (if it is 11, make it 12).

In `templates/assets/detail.html`, after the barcode line (or after product heading content), add before Serial:

```html
    <p><strong>Device Name:</strong> {{ asset.device_name|default:"—" }}</p>
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_asset_create -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/assets/forms.py apps/assets/views.py templates/assets/list.html templates/assets/detail.html apps/assets/tests/test_asset_create.py
git commit -m "Show and search Device Name on asset create, list, and detail."
```

---

### Task 3: Device Name on Quick and Full Batch Scan

**Files:**
- Modify: `apps/scan/forms.py`
- Modify: `apps/scan/batch.py`
- Modify: `templates/scan/batch_home.html`
- Test: `apps/scan/tests/test_batch_scan.py`

**Interfaces:**
- Consumes: `Asset.device_name`, `_update_batch_meta`, `_batch_form`, `MODE_FULL`
- Produces: `BatchItemForm.device_name` (optional, max_length 128). `batch_save` always writes `device_name` from the form (Quick and Full). After success, `_update_batch_meta(..., last_device_name=device_name)` on every successful save; Full still also updates last model/location. `_batch_form` initial always includes `device_name` from `last_device_name`. Template shows Device Name in Quick and Full, after Skip 2nd MAC (before the Full-only Model/Location block). Batch Items column after MAC 2.

- [ ] **Step 1: Write the failing test**

Add to `apps/scan/tests/test_batch_scan.py`:

```python
class BatchDeviceNameTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )

    def test_quick_save_stores_and_remembers_device_name(self):
        response = self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN-DEV",
                "mac_address": "aa:bb:cc:dd:ee:11",
                "device_name": "EPS-AP-01",
                "batch_mode": "quick",
            },
        )
        self.assertRedirects(response, "/scan/batch/")
        asset = Asset.objects.get(serial_number="SN-DEV")
        self.assertEqual(asset.device_name, "EPS-AP-01")
        home = self.client.get("/scan/batch/")
        self.assertContains(home, 'id="id_device_name"')
        self.assertContains(home, 'value="EPS-AP-01"')
        self.assertContains(home, "<th>Device Name</th>")
        self.assertNotContains(home, 'value="SN-DEV"')

    def test_full_save_stores_device_name_with_model_and_location(self):
        self.client.get("/scan/batch/", {"mode": "full"})
        self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN-FULL-DEV",
                "mac_address": "aa:bb:cc:dd:ee:22",
                "device_name": "EPS-Switch-01",
                "model_number": "SP4628",
                "location": "Room1",
                "batch_mode": "full",
            },
        )
        asset = Asset.objects.get(serial_number="SN-FULL-DEV")
        self.assertEqual(asset.device_name, "EPS-Switch-01")
        self.assertEqual(asset.model_number, "SP4628")
        self.assertEqual(asset.location, "Room1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchDeviceNameTests -v 2`

Expected: FAIL — form has no `device_name` / asset field empty

- [ ] **Step 3: Write minimal implementation**

Add to `BatchItemForm` in `apps/scan/forms.py` after `skip_mac_2` (before `model_number`):

```python
    device_name = forms.CharField(
        required=False,
        max_length=128,
        widget=forms.TextInput(
            attrs={"class": "form-input", "id": "id_device_name", "placeholder": "EPS-Switch-01"}
        ),
    )
```

In `batch_start` meta dict, add `"last_device_name": ""`.

In `_batch_form`, always seed device name:

```python
    initial = {
        "device_name": meta.get("last_device_name") or "",
    }
    if mode == MODE_FULL:
        initial["model_number"] = meta.get("last_model_number") or ""
        initial["location"] = meta.get("last_location") or ""
```

In `batch_save` when building `Asset`, add:

```python
            device_name=(form.cleaned_data.get("device_name") or "").strip(),
```

In the success branch, always update last device name; keep Full model/location updates:

```python
            device_name = (form.cleaned_data.get("device_name") or "").strip()
            updates = {"last_device_name": device_name}
            if mode == MODE_FULL:
                updates["last_model_number"] = model_number
                updates["last_location"] = location
            _update_batch_meta(request, key, **updates)
```

(Pass the same stripped `device_name` into `Asset(...)` — do not strip twice inconsistently.)

In `templates/scan/batch_home.html`, after the Skip 2nd MAC row and before `{% if batch_mode == 'full' %}`:

```html
    <div class="field-row">
      <label class="form-label" for="{{ form.device_name.id_for_label }}">Device Name</label>
      <div class="field-row-scan">
        {{ form.device_name }}
        <button type="button" class="btn btn-secondary btn-scan-field" data-scan-target="{{ form.device_name.id_for_label }}" data-scan-label="Device Name">📷 Scan</button>
      </div>
      {% if form.device_name.errors %}<p class="form-error" style="color:var(--danger);font-size:0.875rem">{{ form.device_name.errors.0 }}</p>{% endif %}
    </div>
```

Batch Items header: after MAC 2 add `<th>Device Name</th>`. In the row after MAC 2:

```html
            <td>{{ asset.device_name|default:"—" }}</td>
```

Empty colspan 7 → 8.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan -v 2`

Expected: PASS (existing Quick/Full tests still pass; include `batch_mode` on new posts as shown)

- [ ] **Step 5: Commit**

```bash
git add apps/scan/forms.py apps/scan/batch.py templates/scan/batch_home.html apps/scan/tests/test_batch_scan.py
git commit -m "Capture Device Name on Quick and Full Batch Scan and remember the last value."
```

---

### Task 4: Site/print column picker and Device Name on reports

**Files:**
- Create: `apps/assets/report_columns.py`
- Create: `apps/assets/tests/test_report_columns.py`
- Modify: `apps/assets/barcode_utils.py`
- Modify: `apps/assets/views.py`
- Modify: `templates/assets/print_report.html`
- Modify: `templates/assets/site_report.html`
- Modify: `apps/assets/tests/test_asset_reports.py`

**Interfaces:**
- Consumes: `Asset.device_name`, `assets_have_second_mac`
- Produces:
  - `REPORT_COLUMN_KEYS: tuple[str, ...]`
  - `REPORT_COLUMN_LABELS: dict[str, str]`
  - `parse_report_columns(raw: str | None) -> tuple[str, ...]`
  - `visible_report_columns(column_keys, *, show_mac_2: bool) -> tuple[str, ...]`
  - `asset_report_table_data(assets, column_keys=None) -> tuple[list, bool]` uses parse default when `column_keys` is None
  - `assets_pdf_bytes(assets, title=..., column_keys=None)`
  - `assets_pdf_response(assets, title=..., column_keys=None)`
  - Views pass `column_keys = parse_report_columns(request.GET.get("cols"))` into templates and PDF

- [ ] **Step 1: Write the failing tests**

Create `apps/assets/tests/test_report_columns.py`:

```python
from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model

from apps.assets.barcode_utils import asset_report_table_data
from apps.assets.models import Asset
from apps.assets.report_columns import (
    REPORT_COLUMN_KEYS,
    parse_report_columns,
    visible_report_columns,
)

User = get_user_model()


class ParseReportColumnsTests(SimpleTestCase):
    def test_blank_defaults_to_all(self):
        self.assertEqual(parse_report_columns(None), REPORT_COLUMN_KEYS)
        self.assertEqual(parse_report_columns(""), REPORT_COLUMN_KEYS)
        self.assertEqual(parse_report_columns("nope"), REPORT_COLUMN_KEYS)

    def test_filters_unknown_and_duplicates_and_keeps_canonical_order(self):
        self.assertEqual(
            parse_report_columns("mac,serial,mac,nope,device_name"),
            ("device_name", "serial", "mac"),
        )

    def test_hides_mac_2_when_empty_even_if_selected(self):
        keys = parse_report_columns("serial,mac,mac_2")
        self.assertEqual(visible_report_columns(keys, show_mac_2=False), ("serial", "mac"))
        self.assertEqual(visible_report_columns(keys, show_mac_2=True), ("serial", "mac", "mac_2"))


class ReportColumnPickerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.asset = Asset.objects.create(
            site_name="Test",
            product_name="Switches",
            device_name="EPS-Switch-01",
            serial_number="444444",
            mac_address="AA:BB:CC:DD:EE:01",
            barcode_value="AT-COLS01",
            model_number="SP4628",
            location="Room1",
        )

    def test_default_html_includes_device_name(self):
        response = self.client.get("/assets/report/", {"site": "Test"})
        self.assertContains(response, "<th>Device Name</th>")
        self.assertContains(response, "EPS-Switch-01")
        self.assertContains(response, 'name="cols"')

    def test_cols_query_hides_unselected_fields(self):
        response = self.client.get("/assets/report/", {"site": "Test", "cols": "serial,mac"})
        self.assertContains(response, "<th>Serial</th>")
        self.assertContains(response, "<th>MAC</th>")
        self.assertNotContains(response, "<th>Device Name</th>")
        self.assertNotContains(response, "<th>Location</th>")
        self.assertContains(response, 'href="?site=Test&amp;cols=serial,mac&amp;export=pdf"')

    def test_table_data_follows_selected_columns(self):
        data, _ = asset_report_table_data(
            Asset.objects.filter(pk=self.asset.pk),
            column_keys=("device_name", "serial"),
        )
        self.assertEqual(data[0], ["Device Name", "Serial"])
        self.assertEqual(data[1][0], "EPS-Switch-01")
        self.assertEqual(data[1][1], "444444")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_report_columns -v 2`

Expected: FAIL — `No module named 'apps.assets.report_columns'`

- [ ] **Step 3: Write minimal implementation**

Create `apps/assets/report_columns.py`:

```python
REPORT_COLUMN_KEYS = (
    "number",
    "barcode",
    "site",
    "product",
    "device_name",
    "serial",
    "mac",
    "mac_2",
    "model",
    "location",
    "comments",
)

REPORT_COLUMN_LABELS = {
    "number": "#",
    "barcode": "Barcode",
    "site": "Site",
    "product": "Product",
    "device_name": "Device Name",
    "serial": "Serial",
    "mac": "MAC",
    "mac_2": "MAC 2",
    "model": "Model",
    "location": "Location",
    "comments": "Comments",
}


def parse_report_columns(raw) -> tuple:
    allowed = set(REPORT_COLUMN_KEYS)
    seen = []
    for part in (raw or "").split(","):
        key = part.strip()
        if key in allowed and key not in seen:
            seen.append(key)
    if not seen:
        return REPORT_COLUMN_KEYS
    return tuple(key for key in REPORT_COLUMN_KEYS if key in seen)


def visible_report_columns(column_keys, *, show_mac_2: bool) -> tuple:
    keys = tuple(column_keys or REPORT_COLUMN_KEYS)
    if not show_mac_2:
        keys = tuple(key for key in keys if key != "mac_2")
    return keys


def report_column_cells(asset, *, show_mac_2: bool) -> dict:
    comments = asset.comments or "—"
    if asset.comments and len(asset.comments) > 40:
        comments = asset.comments[:40] + "…"
    cells = {
        "number": str(asset.asset_number or "—"),
        "barcode": asset.barcode_value,
        "site": (asset.site_name[:20] or "—"),
        "product": asset.product_name[:30],
        "device_name": (asset.device_name[:40] or "—"),
        "serial": (asset.serial_number[:20] or "—"),
        "mac": (asset.mac_address[:17] or "—"),
        "model": (asset.model_number[:20] or "—"),
        "location": (asset.location[:20] or "—"),
        "comments": comments,
    }
    if show_mac_2:
        cells["mac_2"] = asset.mac_address_2[:17] or "—"
    return cells
```

Replace `asset_report_table_data` in `apps/assets/barcode_utils.py` so it imports those helpers and builds rows from selected keys:

```python
from apps.assets.report_columns import (
    REPORT_COLUMN_LABELS,
    parse_report_columns,
    report_column_cells,
    visible_report_columns,
)


def asset_report_table_data(assets, column_keys=None):
    show_mac_2 = assets_have_second_mac(assets)
    keys = visible_report_columns(column_keys or parse_report_columns(None), show_mac_2=show_mac_2)
    data = [[REPORT_COLUMN_LABELS[key] for key in keys]]
    for asset in assets:
        cells = report_column_cells(asset, show_mac_2=show_mac_2)
        data.append([cells[key] for key in keys])
    return data, show_mac_2
```

Change `assets_pdf_bytes` and `assets_pdf_response` to accept `column_keys=None` and pass it through to `asset_report_table_data`. Email keeps calling `assets_pdf_bytes(assets, title=title)` with no keys (all columns, including Device Name).

In `print_report` and `site_report_view`:

```python
from apps.assets.report_columns import REPORT_COLUMN_KEYS, REPORT_COLUMN_LABELS, parse_report_columns, visible_report_columns
```

```python
    column_keys = parse_report_columns(request.GET.get("cols"))
    show_mac_2 = assets_have_second_mac(assets)
    visible_keys = visible_report_columns(column_keys, show_mac_2=show_mac_2)
    cols_query = ",".join(column_keys)
```

For PDF export in `print_report`, pass `column_keys=column_keys` into `assets_pdf_response`.

Template context must include: `show_mac_2`, `column_keys`, `visible_keys`, `report_columns` as a list of `{key, label, selected}` for every key in `REPORT_COLUMN_KEYS` (`selected` if key in `column_keys`; for `mac_2` still listed in the picker even if the table omits it), plus `cols_query`.

Site report PDF button already points at `assets:report` with `site=`. Update it to include `&cols={{ cols_query }}` when `cols_query` is present.

In both report templates, above the table, add a no-print Columns form. Example for print_report (preserve `site`, `ids`, `session` from `request.GET`):

```html
  <form method="get" class="no-print" style="margin:1rem 0">
    {% if request.GET.site %}<input type="hidden" name="site" value="{{ request.GET.site }}">{% endif %}
    {% if request.GET.ids %}<input type="hidden" name="ids" value="{{ request.GET.ids }}">{% endif %}
    {% if request.GET.session %}<input type="hidden" name="session" value="{{ request.GET.session }}">{% endif %}
    <p style="margin:0 0 0.5rem"><strong>Columns</strong></p>
    {% for col in report_columns %}
    <label style="margin-right:0.75rem">
      <input type="checkbox" name="col" value="{{ col.key }}" {% if col.selected %}checked{% endif %}>
      {{ col.label }}
    </label>
    {% endfor %}
    <noscript><button type="submit" class="btn btn-secondary">Apply</button></noscript>
  </form>
  <script>
  document.querySelectorAll('input[name=col]').forEach(box => {
    box.addEventListener('change', () => {
      const form = box.form;
      const keys = Array.from(form.querySelectorAll('input[name=col]:checked')).map(el => el.value);
      const params = new URLSearchParams(new FormData(form));
      params.delete('col');
      params.set('cols', keys.join(','));
      window.location.search = params.toString();
    });
  });
  </script>
```

Render table headers from `visible_keys` using `REPORT_COLUMN_LABELS` passed as `column_labels` or precomputed `visible_headers`. Render each body cell from the matching asset attribute:

| key | template value |
|-----|----------------|
| number | `asset.asset_number\|default:"—"` |
| barcode | `asset.barcode_value` |
| site | `asset.site_name\|default:"—"` |
| product | `asset.product_name` |
| device_name | `asset.device_name\|default:"—"` |
| serial | `asset.serial_number\|default:"—"` |
| mac | `asset.mac_address\|default:"—"` |
| mac_2 | `asset.mac_address_2\|default:"—"` |
| model | `asset.model_number\|default:"—"` |
| location | `asset.location\|default:"—"` |
| comments | `asset.comments\|default:"—"` |

Simplest: in the view, do not pass a lookup dict into Django templates — pass `visible_headers` (list of labels) and for each asset build nothing extra; use `{% for key in visible_keys %}{% if key == "serial" %}...`. That is verbose. Prefer a small template include `templates/assets/report_cells.html` with `{% if key == "number" %}...`.

Create `templates/assets/_report_cell.html`:

```html
{% if key == "number" %}{{ asset.asset_number|default:"—" }}
{% elif key == "barcode" %}{{ asset.barcode_value }}
{% elif key == "site" %}{{ asset.site_name|default:"—" }}
{% elif key == "product" %}{{ asset.product_name }}
{% elif key == "device_name" %}{{ asset.device_name|default:"—" }}
{% elif key == "serial" %}{{ asset.serial_number|default:"—" }}
{% elif key == "mac" %}{{ asset.mac_address|default:"—" }}
{% elif key == "mac_2" %}{{ asset.mac_address_2|default:"—" }}
{% elif key == "model" %}{{ asset.model_number|default:"—" }}
{% elif key == "location" %}{{ asset.location|default:"—" }}
{% elif key == "comments" %}{{ asset.comments|default:"—" }}
{% endif %}
```

Print PDF link:

```html
<a href="?export=pdf{% if request.GET.ids %}&ids={{ request.GET.ids }}{% endif %}{% if request.GET.session %}&session={{ request.GET.session }}{% endif %}{% if request.GET.site %}&site={{ request.GET.site|urlencode }}{% endif %}{% if cols_query %}&cols={{ cols_query }}{% endif %}">Download PDF</a>
```

The `test_cols_query_hides_unselected_fields` href assertion may need to match whatever order/escaping Django produces; if `&amp;export=pdf` order differs, assertContains each of `cols=serial,mac` and `export=pdf` separately.

Update `apps/assets/tests/test_asset_reports.py` MAC index assertions: do not assume MAC is column 5. Use `self.assertIn("MAC", data[0])` and `self.assertNotIn("MAC 2", data[0])`, and find the MAC cell with `data[0].index("MAC")`.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_report_columns apps.assets.tests.test_asset_reports -v 2`

Expected: PASS

Then: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan apps.assets.tests.test_asset_create -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/assets/report_columns.py apps/assets/tests/test_report_columns.py apps/assets/barcode_utils.py apps/assets/views.py apps/assets/tests/test_asset_reports.py templates/assets/print_report.html templates/assets/site_report.html templates/assets/_report_cell.html
git commit -m "Add Device Name to site reports and let users pick columns, defaulting to all."
```

---

## Spec coverage

- Device Name field/migration — Task 1
- Create/edit/list/detail/search — Task 2
- Quick/Full batch capture + remember last — Task 3
- Batch Items column — Task 3
- Site/print HTML + PDF Device Name — Task 4
- `cols` picker default all, canonical order, unknown fallback — Task 4
- MAC 2 omit when empty though selected — Task 4
- Email PDF all columns including Device Name (default `assets_pdf_bytes`) — Task 4
- Out of scope labels / uniqueness / batch report picker — no tasks
