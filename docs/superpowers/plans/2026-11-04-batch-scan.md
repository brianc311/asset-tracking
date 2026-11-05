# Batch Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Batch Scan page that records site + device type + serial + MAC(s) on existing Assets, with no duplicates, archive, barcode reports, and two label modes.

**Architecture:** Keep data on `Asset`. Add `mac_address` / `mac_address_2` plus a MAC normalizer. Batch Scan is a new session flow in `apps.scan` (separate session keys from `/scan/`). Reports and labels read selected or current-batch assets and render Code 128 barcodes for serial and each MAC.

**Tech Stack:** Django 5, existing `python-barcode` / ReportLab / `field-scanner.js`, Django `TestCase` via `manage.py test`.

## Global Constraints

- Extend existing `Asset` — do not create Site, Batch, or intake tables.
- Serial unique among non-archived assets at the same site. No override.
- MAC 1 and MAC 2 unique among non-archived assets everywhere (either MAC field). No override.
- MAC 2 required unless `skip_mac_2` is checked; then store blank.
- Normalize MACs to `AA:BB:CC:DD:EE:FF`.
- Timestamp is `Asset.created_at`.
- Device type is `Asset.product_name` (AP, Switch, or typed value).
- Do not replace `/scan/` or require photos/model/location/comments on Batch Scan.
- Staff+ only (`user.can_manage_assets()`), same as Scan.
- Run tests with: `.\.venv\Scripts\python.exe manage.py test <dotted.path> -v 2`

## File map

- Create: `apps/assets/mac.py` — normalize/validate MAC strings
- Create: `apps/assets/product_types.py` — known product names + select/add-new (same pattern as site names)
- Create: `apps/assets/migrations/0004_asset_mac_addresses.py`
- Create: `apps/assets/tests/__init__.py`
- Create: `apps/assets/tests/test_mac.py`
- Create: `apps/assets/tests/test_asset_mac_uniqueness.py`
- Create: `apps/scan/batch.py` — session helpers + batch views
- Create: `apps/scan/tests/__init__.py`
- Create: `apps/scan/tests/test_batch_scan.py`
- Create: `apps/scan/tests/test_batch_report_labels.py`
- Create: `templates/scan/batch_start.html`
- Create: `templates/scan/batch_home.html`
- Create: `templates/scan/batch_report.html`
- Create: `templates/scan/batch_labels.html`
- Create: `static/js/batch-scan.js`
- Create: `templates/assets/product_type_fields.html`
- Modify: `apps/assets/models.py` — MAC fields + `clean()` uniqueness
- Modify: `apps/assets/forms.py` — MAC fields on AssetForm so edit works
- Modify: `apps/assets/views.py` — search includes MACs
- Modify: `apps/assets/barcode_utils.py` — barcode for an arbitrary value
- Modify: `apps/scan/forms.py` — `StartBatchForm`, `BatchItemForm`
- Modify: `apps/scan/urls.py` — `/scan/batch/` routes
- Modify: `templates/base.html` — Batch Scan nav link
- Modify: `templates/assets/list.html` and `templates/assets/detail.html` — show MACs
- Modify: `templates/assets/form.html` if it loops fields (include new fields automatically via form)

---

### Task 1: MAC normalizer

**Files:**
- Create: `apps/assets/mac.py`
- Create: `apps/assets/tests/__init__.py`
- Test: `apps/assets/tests/test_mac.py`

**Interfaces:**
- Consumes: none
- Produces: `normalize_mac(value: str) -> str` raises `ValueError`; `MAC_ERROR = "Enter a 12-digit MAC address."`

- [ ] **Step 1: Write the failing test**

Create `apps/assets/tests/__init__.py` (empty) and `apps/assets/tests/test_mac.py`:

```python
from django.test import SimpleTestCase

from apps.assets.mac import MAC_ERROR, normalize_mac


class NormalizeMacTests(SimpleTestCase):
    def test_colon_form(self):
        self.assertEqual(normalize_mac("aa:bb:cc:dd:ee:ff"), "AA:BB:CC:DD:EE:FF")

    def test_hyphen_and_bare_hex(self):
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-ff"), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(normalize_mac("aabbccddeeff"), "AA:BB:CC:DD:EE:FF")

    def test_rejects_invalid(self):
        with self.assertRaisesMessage(ValueError, MAC_ERROR):
            normalize_mac("not-a-mac")
        with self.assertRaisesMessage(ValueError, MAC_ERROR):
            normalize_mac("")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_mac -v 2`

Expected: FAIL — `ModuleNotFoundError: No module named 'apps.assets.mac'`

- [ ] **Step 3: Write minimal implementation**

Create `apps/assets/mac.py`:

```python
import re

MAC_ERROR = "Enter a 12-digit MAC address."
_HEX = re.compile(r"[^0-9A-Fa-f]")


def normalize_mac(value: str) -> str:
    hex_only = _HEX.sub("", value or "")
    if len(hex_only) != 12:
        raise ValueError(MAC_ERROR)
    hex_only = hex_only.upper()
    return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_mac -v 2`

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/assets/mac.py apps/assets/tests/__init__.py apps/assets/tests/test_mac.py
git commit -m "Add MAC address normalizer for batch scan."
```

---

### Task 2: Asset MAC fields and uniqueness

**Files:**
- Modify: `apps/assets/models.py`
- Create: `apps/assets/migrations/0004_asset_mac_addresses.py`
- Test: `apps/assets/tests/test_asset_mac_uniqueness.py`

**Interfaces:**
- Consumes: `normalize_mac(value: str) -> str`
- Produces: `Asset.mac_address`, `Asset.mac_address_2`; `Asset.clean()` raises `ValidationError` on duplicate serial (same site, not archived) or duplicate MAC (any site, either field, not archived)

- [ ] **Step 1: Write the failing test**

```python
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.assets.models import Asset


def make_asset(**kwargs):
    defaults = {
        "product_name": "AP",
        "barcode_value": kwargs.pop("barcode_value", f"AT-{kwargs.get('serial_number', 'X')}"),
        "site_name": "SiteA",
        "serial_number": "SN1",
    }
    defaults.update(kwargs)
    return Asset.objects.create(**defaults)


class AssetMacUniquenessTests(TestCase):
    def test_duplicate_serial_same_site_rejected(self):
        make_asset(serial_number="SN1", mac_address="AA:BB:CC:DD:EE:01")
        asset = Asset(
            product_name="AP",
            site_name="SiteA",
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:02",
            barcode_value="AT-DUP-SN",
        )
        with self.assertRaises(ValidationError):
            asset.full_clean()

    def test_same_serial_other_site_allowed(self):
        make_asset(serial_number="SN1", mac_address="AA:BB:CC:DD:EE:01")
        asset = Asset(
            product_name="AP",
            site_name="SiteB",
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:02",
            barcode_value="AT-OTHER-SITE",
        )
        asset.full_clean()

    def test_duplicate_mac_any_site_rejected(self):
        make_asset(serial_number="SN1", mac_address="AA:BB:CC:DD:EE:01", site_name="SiteA")
        asset = Asset(
            product_name="Switch",
            site_name="SiteB",
            serial_number="SN9",
            mac_address="AA:BB:CC:DD:EE:01",
            barcode_value="AT-DUP-MAC",
        )
        with self.assertRaises(ValidationError):
            asset.full_clean()

    def test_mac_matches_other_mac_2_rejected(self):
        make_asset(
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:01",
            mac_address_2="AA:BB:CC:DD:EE:99",
        )
        asset = Asset(
            product_name="AP",
            site_name="SiteB",
            serial_number="SN2",
            mac_address="AA:BB:CC:DD:EE:99",
            barcode_value="AT-DUP-MAC2",
        )
        with self.assertRaises(ValidationError):
            asset.full_clean()

    def test_archived_serial_does_not_block(self):
        make_asset(serial_number="SN1", mac_address="AA:BB:CC:DD:EE:01", is_archived=True)
        asset = Asset(
            product_name="AP",
            site_name="SiteA",
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:02",
            barcode_value="AT-REUSE",
        )
        asset.full_clean()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_asset_mac_uniqueness -v 2`

Expected: FAIL — `Asset()` unexpected keyword `mac_address`

- [ ] **Step 3: Add fields, `clean()`, and migration**

Add to `Asset` in `apps/assets/models.py` after `serial_number`:

```python
    mac_address = models.CharField(max_length=17, blank=True, db_index=True)
    mac_address_2 = models.CharField(max_length=17, blank=True, db_index=True)
```

Add `clean()` on `Asset` (import `ValidationError` from `django.core.exceptions` and `Q` from `django.db.models`):

```python
    def clean(self):
        from django.core.exceptions import ValidationError
        from django.db.models import Q

        super().clean()
        errors = {}
        serial = (self.serial_number or "").strip()
        site = (self.site_name or "").strip()
        macs = [m for m in (self.mac_address, self.mac_address_2) if m]

        if serial and site:
            qs = Asset.objects.filter(
                is_archived=False, site_name=site, serial_number=serial
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors["serial_number"] = "This serial is already used at this site."

        if len(macs) == 2 and macs[0] == macs[1]:
            errors["mac_address_2"] = "MAC 2 must be different from MAC 1."

        for field_name, value in (
            ("mac_address", self.mac_address),
            ("mac_address_2", self.mac_address_2),
        ):
            if not value:
                continue
            qs = Asset.objects.filter(is_archived=False).filter(
                Q(mac_address=value) | Q(mac_address_2=value)
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors[field_name] = "This MAC address is already in use."

        if errors:
            raise ValidationError(errors)
```

Create migration `apps/assets/migrations/0004_asset_mac_addresses.py`:

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0003_asset_site_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="mac_address",
            field=models.CharField(blank=True, db_index=True, max_length=17),
        ),
        migrations.AddField(
            model_name="asset",
            name="mac_address_2",
            field=models.CharField(blank=True, db_index=True, max_length=17),
        ),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_asset_mac_uniqueness -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/assets/models.py apps/assets/migrations/0004_asset_mac_addresses.py apps/assets/tests/test_asset_mac_uniqueness.py
git commit -m "Add asset MAC fields and reject duplicate serials and MACs."
```

---

### Task 3: Product type helper and batch forms

**Files:**
- Create: `apps/assets/product_types.py`
- Create: `templates/assets/product_type_fields.html`
- Modify: `apps/scan/forms.py`
- Modify: `apps/assets/forms.py`
- Test: `apps/scan/tests/__init__.py` (empty) and `apps/scan/tests/test_batch_scan.py` (form cases only in this task)

**Interfaces:**
- Consumes: `normalize_mac`, `NEW_SITE_VALUE` / `resolve_site_name` / `apply_site_name_choices`
- Produces:
  - `NEW_PRODUCT_VALUE = "__new__"`
  - `get_known_product_names() -> list[str]`
  - `apply_product_type_fields(form, known_product_names, *, default_product_name="")`
  - `resolve_product_name(cleaned_data, *, errors_form=None) -> str`
  - `StartBatchForm` fields: `site_name`, `new_site_name`, `product_name`, `new_product_name`
  - `BatchItemForm` fields: `serial_number`, `mac_address`, `mac_address_2`, `skip_mac_2`
  - `AssetForm` includes `mac_address` and `mac_address_2`

- [ ] **Step 1: Write the failing form tests**

Append to `apps/scan/tests/test_batch_scan.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.assets.models import Asset
from apps.scan.forms import BatchItemForm, StartBatchForm

User = get_user_model()


class BatchFormTests(TestCase):
    def test_start_requires_site_and_type(self):
        form = StartBatchForm(data={"site_name": "", "product_name": ""}, known_site_names=[], known_product_names=[])
        self.assertFalse(form.is_valid())

    def test_skip_mac_2_allows_blank(self):
        form = BatchItemForm(
            data={
                "serial_number": "SN1",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "mac_address_2": "",
                "skip_mac_2": "on",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["mac_address"], "AA:BB:CC:DD:EE:01")
        self.assertEqual(form.cleaned_data["mac_address_2"], "")

    def test_mac_2_required_when_not_skipped(self):
        form = BatchItemForm(
            data={
                "serial_number": "SN1",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "mac_address_2": "",
                "skip_mac_2": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("mac_address_2", form.errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchFormTests -v 2`

Expected: FAIL — cannot import `StartBatchForm` / `BatchItemForm`

- [ ] **Step 3: Implement helper and forms**

Create `apps/assets/product_types.py` by copying the site-name pattern:

```python
from django import forms

from apps.assets.models import Asset

NEW_PRODUCT_VALUE = "__new__"


def get_known_product_names():
    names = set(
        Asset.objects.exclude(product_name="")
        .values_list("product_name", flat=True)
        .distinct()
    )
    return sorted(names, key=str.lower)


def apply_product_type_fields(form, known_product_names, *, default_product_name=""):
    current = (default_product_name or "").strip()
    names = list(known_product_names or [])
    if current and current not in names:
        names.append(current)
    names = sorted(set(names), key=str.lower)

    choices = [("", "Select a type…")]
    choices.extend((name, name) for name in names)
    choices.append((NEW_PRODUCT_VALUE, "+ Add new type…"))

    form.fields["product_name"] = forms.ChoiceField(
        choices=choices,
        required=False,
        label="Device type",
        widget=forms.Select(attrs={"class": "form-input product-name-select"}),
    )
    form.fields["new_product_name"] = forms.CharField(
        required=False,
        label="New device type",
        widget=forms.TextInput(
            attrs={
                "class": "form-input new-product-name-input",
                "placeholder": "e.g. AP, Switch",
            }
        ),
    )
    if current and any(value == current for value, _ in choices):
        form.fields["product_name"].initial = current
    elif current:
        form.fields["product_name"].initial = NEW_PRODUCT_VALUE
        form.fields["new_product_name"].initial = current


def resolve_product_name(cleaned_data, *, default_product_name="", errors_form=None):
    name = cleaned_data.get("product_name", "")
    if name == NEW_PRODUCT_VALUE:
        name = (cleaned_data.get("new_product_name") or "").strip()
    elif name:
        name = name.strip()
    elif default_product_name:
        name = default_product_name.strip()

    if not name and errors_form is not None:
        errors_form.add_error("product_name", "Please select or enter a device type.")

    cleaned_data["product_name"] = name
    return name
```

Create `templates/assets/product_type_fields.html`:

```html
<label class="form-label">{{ form.product_name.label }}</label>
{{ form.product_name }}
{% if form.product_name.errors %}<p class="form-error">{{ form.product_name.errors.0 }}</p>{% endif %}
<div class="new-product-name-wrap" hidden>
  <label class="form-label">{{ form.new_product_name.label }}</label>
  {{ form.new_product_name }}
</div>
```

Add to `apps/scan/forms.py`:

```python
from apps.assets.mac import MAC_ERROR, normalize_mac
from apps.assets.product_types import apply_product_type_fields, resolve_product_name


class StartBatchForm(forms.Form):
    def __init__(self, *args, known_site_names=None, known_product_names=None, default_site_name="", default_product_name="", **kwargs):
        super().__init__(*args, **kwargs)
        apply_site_name_choices(self, known_site_names, default_site_name=default_site_name)
        apply_product_type_fields(self, known_product_names, default_product_name=default_product_name)
        self.fields["site_name"].help_text = "Site for this batch."
        self.fields["product_name"].help_text = "Scan all of this type, then change type for the next batch."

    def clean(self):
        cleaned_data = super().clean()
        resolve_site_name(cleaned_data, errors_form=self)
        resolve_product_name(cleaned_data, errors_form=self)
        return cleaned_data


class BatchItemForm(forms.Form):
    serial_number = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={"class": "form-input", "id": "id_serial_number", "placeholder": "Serial number"}),
    )
    mac_address = forms.CharField(
        max_length=17,
        widget=forms.TextInput(attrs={"class": "form-input", "id": "id_mac_address", "placeholder": "MAC address"}),
    )
    mac_address_2 = forms.CharField(
        required=False,
        max_length=17,
        widget=forms.TextInput(attrs={"class": "form-input", "id": "id_mac_address_2", "placeholder": "Second MAC"}),
    )
    skip_mac_2 = forms.BooleanField(required=False, label="Skip 2nd MAC")

    def _clean_mac(self, raw):
        try:
            return normalize_mac(raw)
        except ValueError:
            raise forms.ValidationError(MAC_ERROR)

    def clean_mac_address(self):
        return self._clean_mac(self.cleaned_data.get("mac_address", ""))

    def clean_mac_address_2(self):
        raw = self.cleaned_data.get("mac_address_2", "")
        if not raw:
            return ""
        return self._clean_mac(raw)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("skip_mac_2"):
            cleaned["mac_address_2"] = ""
        elif not cleaned.get("mac_address_2"):
            self.add_error("mac_address_2", "Enter the second MAC or check Skip 2nd MAC.")
        return cleaned
```

Add `mac_address` and `mac_address_2` to `AssetForm.Meta.fields` and `ASSET_FIELD_ORDER` (after `serial_number`) with `forms.TextInput(attrs={"class": "form-input"})`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchFormTests -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/assets/product_types.py apps/scan/forms.py apps/assets/forms.py templates/assets/product_type_fields.html apps/scan/tests
git commit -m "Add batch scan forms and device type picker."
```

---

### Task 4: Batch session views, page, and nav

**Files:**
- Create: `apps/scan/batch.py`
- Modify: `apps/scan/urls.py`
- Create: `templates/scan/batch_start.html`
- Create: `templates/scan/batch_home.html`
- Create: `static/js/batch-scan.js`
- Modify: `templates/base.html` (add Batch Scan link next to Scan)

**Interfaces:**
- Consumes: `StartBatchForm`, `BatchItemForm`
- Produces:
  - Session keys: `batch_session_key`, `batch_sessions_meta` (`{key: {site_name, product_name, started_at}}`), `session[key] = [asset ids]`
  - URLs: `scan:batch_start` `/scan/batch/start/`, `scan:batch_home` `/scan/batch/`, `scan:batch_save` POST `/scan/batch/save/`, `scan:batch_archive` POST `/scan/batch/archive/`, `scan:batch_end` POST `/scan/batch/end/`, `scan:batch_report` `/scan/batch/report/`, `scan:batch_labels` `/scan/batch/labels/`
  - Helpers: `get_batch_session(request)`, `require_active_batch(request) -> tuple[str, dict, str, str] | redirect parts`

- [ ] **Step 1: Write the failing view test**

Add to `apps/scan/tests/test_batch_scan.py`:

```python
class BatchViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)

    def test_start_get_ok(self):
        response = self.client.get("/scan/batch/start/")
        self.assertEqual(response.status_code, 200)

    def test_home_redirects_without_session(self):
        response = self.client.get("/scan/batch/")
        self.assertRedirects(response, "/scan/batch/start/")

    def test_start_post_opens_home(self):
        response = self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )
        self.assertRedirects(response, "/scan/batch/")
        follow = self.client.get("/scan/batch/")
        self.assertContains(follow, "HQ")
        self.assertContains(follow, "AP")
        self.assertContains(follow, "Skip 2nd MAC")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchViewTests -v 2`

Expected: FAIL — 404 on `/scan/batch/start/`

- [ ] **Step 3: Implement session helpers, start/home, templates, nav**

Create `apps/scan/batch.py` with session helpers and `batch_start` / `batch_home` (save/archive/report/labels can be stubs that `raise NotImplementedError` only if tests do not hit them yet — instead implement start/home now and add empty-safe placeholders that redirect home so URLs exist):

```python
import uuid

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from apps.assets.models import Asset
from apps.assets.product_types import get_known_product_names
from apps.assets.site_names import get_known_site_names
from apps.scan.forms import BatchItemForm, StartBatchForm

BATCH_KEY = "batch_session_key"
BATCH_META = "batch_sessions_meta"


def _get_meta(request, key):
    return request.session.get(BATCH_META, {}).get(key, {})


def require_active_batch(request):
    key = request.session.get(BATCH_KEY)
    meta = _get_meta(request, key) if key else {}
    site = (meta.get("site_name") or "").strip()
    product = (meta.get("product_name") or "").strip()
    if not key or not site or not product:
        return None, None, None, None
    return key, meta, site, product


def _session_assets(request, key):
    ids = request.session.get(key, [])
    return Asset.objects.filter(pk__in=ids, is_archived=False).order_by("-created_at")


@login_required
def batch_start(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")
    form = StartBatchForm(
        request.POST or None,
        known_site_names=get_known_site_names(request),
        known_product_names=get_known_product_names(),
    )
    if request.method == "POST" and form.is_valid():
        key = f"batch_{uuid.uuid4().hex[:12]}"
        request.session[BATCH_KEY] = key
        request.session[key] = []
        meta = request.session.get(BATCH_META, {})
        meta[key] = {
            "site_name": form.cleaned_data["site_name"],
            "product_name": form.cleaned_data["product_name"],
            "started_at": timezone.now().isoformat(),
        }
        request.session[BATCH_META] = meta
        request.session.modified = True
        return redirect("scan:batch_home")
    return render(request, "scan/batch_start.html", {"form": form})


@login_required
def batch_home(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")
    started = meta.get("started_at")
    started_display = ""
    if started:
        parsed = parse_datetime(started)
        if parsed:
            started_display = timezone.localtime(parsed).strftime("%b %d, %Y %I:%M %p")
    return render(
        request,
        "scan/batch_home.html",
        {
            "form": BatchItemForm(),
            "assets": _session_assets(request, key),
            "site_name": site,
            "product_name": product,
            "started_at_display": started_display,
        },
    )
```

Add URL routes in `apps/scan/urls.py`:

```python
from apps.scan import batch

# inside urlpatterns:
    path("batch/", batch.batch_home, name="batch_home"),
    path("batch/start/", batch.batch_start, name="batch_start"),
    path("batch/save/", batch.batch_save, name="batch_save"),
    path("batch/archive/", batch.batch_archive, name="batch_archive"),
    path("batch/end/", batch.batch_end, name="batch_end"),
    path("batch/report/", batch.batch_report, name="batch_report"),
    path("batch/labels/", batch.batch_labels, name="batch_labels"),
```

For this task only, add stub views in `batch.py` so URL reverse works:

```python
@login_required
@require_POST
def batch_save(request):
    return redirect("scan:batch_home")


@login_required
@require_POST
def batch_archive(request):
    return redirect("scan:batch_home")


@login_required
@require_POST
def batch_end(request):
    key = request.session.get(BATCH_KEY)
    if key:
        meta = request.session.get(BATCH_META, {})
        meta.pop(key, None)
        request.session.pop(key, None)
        request.session[BATCH_META] = meta
        request.session.pop(BATCH_KEY, None)
        request.session.modified = True
    return redirect("scan:batch_start")


@login_required
def batch_report(request):
    return redirect("scan:batch_home")


@login_required
def batch_labels(request):
    return redirect("scan:batch_home")
```

`templates/scan/batch_start.html`: copy `templates/scan/start.html`, title “Start Batch Scan”, include `assets/site_name_fields.html` and `assets/product_type_fields.html`, POST to `scan:batch_start`. In `extra_js` load `site-name-select.js` and a 10-line inline script that toggles `.new-product-name-wrap` when `.product-name-select` is `__new__` (same logic as `static/js/site-name-select.js`).

`templates/scan/batch_home.html`: show site, type, started time; form POST to `scan:batch_save` with serial, MAC 1, MAC 2, Skip 2nd MAC checkbox (`id="id_skip_mac_2"`), scan buttons using `data-scan-target` / `data-scan-label` like other scan fields; table of session assets with checkboxes `class="row-select"`; buttons Archive selected, Print report, Print labels, End batch. Load `{% static 'js/field-scanner.js' %}` and `{% static 'js/batch-scan.js' %}`.

`static/js/batch-scan.js`:

```javascript
function syncSkipMac2() {
  const skip = document.getElementById('id_skip_mac_2');
  const wrap = document.getElementById('mac-2-wrap');
  const input = document.getElementById('id_mac_address_2');
  if (!skip || !wrap) return;
  const on = skip.checked;
  wrap.hidden = on;
  if (on && input) input.value = '';
}

document.addEventListener('DOMContentLoaded', () => {
  const skip = document.getElementById('id_skip_mac_2');
  if (skip) {
    skip.addEventListener('change', syncSkipMac2);
    syncSkipMac2();
  }
});
```

In `templates/base.html` after the Scan link:

```html
{% if user.can_manage_assets %}<a href="{% url 'scan:batch_start' %}">Batch Scan</a>{% endif %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchViewTests -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/scan/batch.py apps/scan/urls.py templates/scan/batch_start.html templates/scan/batch_home.html static/js/batch-scan.js templates/base.html
git commit -m "Add Batch Scan start and home pages."
```

---

### Task 5: Save batch items (skip MAC 2 + hard duplicate reject)

**Files:**
- Modify: `apps/scan/batch.py` (`batch_save`)
- Test: `apps/scan/tests/test_batch_scan.py`

**Interfaces:**
- Consumes: `BatchItemForm`, `require_active_batch`, `Asset.full_clean()` / `Asset.save()`
- Produces: `batch_save(request)` creates `Asset(site_name, product_name, serial_number, mac_address, mac_address_2, created_by, updated_by)` and appends pk to `request.session[key]`

- [ ] **Step 1: Write the failing tests**

```python
class BatchSaveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )

    def test_skip_mac_2_saves_blank(self):
        response = self.client.post(
            "/scan/batch/save/",
            {"serial_number": "SN1", "mac_address": "aa:bb:cc:dd:ee:01", "mac_address_2": "", "skip_mac_2": "on"},
        )
        self.assertRedirects(response, "/scan/batch/")
        asset = Asset.objects.get(serial_number="SN1")
        self.assertEqual(asset.mac_address, "AA:BB:CC:DD:EE:01")
        self.assertEqual(asset.mac_address_2, "")
        self.assertEqual(asset.site_name, "HQ")
        self.assertEqual(asset.product_name, "AP")
        self.assertIsNotNone(asset.created_at)

    def test_missing_mac_2_rejected(self):
        self.client.post(
            "/scan/batch/save/",
            {"serial_number": "SN1", "mac_address": "aa:bb:cc:dd:ee:01", "mac_address_2": ""},
        )
        self.assertFalse(Asset.objects.filter(serial_number="SN1").exists())

    def test_duplicate_serial_same_site_rejected(self):
        Asset.objects.create(
            product_name="AP",
            site_name="HQ",
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:99",
            barcode_value="AT-EXIST",
        )
        response = self.client.post(
            "/scan/batch/save/",
            {"serial_number": "SN1", "mac_address": "aa:bb:cc:dd:ee:01", "skip_mac_2": "on"},
        )
        self.assertEqual(Asset.objects.filter(serial_number="SN1").count(), 1)
        self.assertContains(response, "already used", status_code=200)

    def test_duplicate_mac_rejected(self):
        Asset.objects.create(
            product_name="Switch",
            site_name="Other",
            serial_number="SN9",
            mac_address="AA:BB:CC:DD:EE:01",
            barcode_value="AT-EXIST-MAC",
        )
        response = self.client.post(
            "/scan/batch/save/",
            {"serial_number": "SN2", "mac_address": "aa:bb:cc:dd:ee:01", "skip_mac_2": "on"},
        )
        self.assertFalse(Asset.objects.filter(serial_number="SN2").exists())
        self.assertContains(response, "already in use", status_code=200)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchSaveTests -v 2`

Expected: FAIL — no asset created (`batch_save` still redirects without saving)

- [ ] **Step 3: Implement `batch_save`**

Replace the stub:

```python
from django.core.exceptions import ValidationError

@login_required
@require_POST
def batch_save(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")

    form = BatchItemForm(request.POST)
    if form.is_valid():
        asset = Asset(
            site_name=site,
            product_name=product,
            serial_number=form.cleaned_data["serial_number"].strip(),
            mac_address=form.cleaned_data["mac_address"],
            mac_address_2=form.cleaned_data["mac_address_2"],
            created_by=request.user,
            updated_by=request.user,
        )
        try:
            asset.full_clean()
            asset.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            ids = request.session.get(key, [])
            ids.append(asset.pk)
            request.session[key] = ids
            request.session.modified = True
            return redirect("scan:batch_home")

    started = meta.get("started_at")
    started_display = ""
    if started:
        parsed = parse_datetime(started)
        if parsed:
            started_display = timezone.localtime(parsed).strftime("%b %d, %Y %I:%M %p")
    return render(
        request,
        "scan/batch_home.html",
        {
            "form": form,
            "assets": _session_assets(request, key),
            "site_name": site,
            "product_name": product,
            "started_at_display": started_display,
        },
        status=200,
    )
```

On `batch_home.html`, render `{{ form.non_field_errors }}` and field errors.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchSaveTests -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/scan/batch.py templates/scan/batch_home.html apps/scan/tests/test_batch_scan.py
git commit -m "Save batch scans and reject duplicate serials and MACs."
```

---

### Task 6: Archive selected batch rows

**Files:**
- Modify: `apps/scan/batch.py` (`batch_archive`)
- Modify: `templates/scan/batch_home.html` (archive form posts `asset_ids`)
- Test: `apps/scan/tests/test_batch_scan.py`

**Interfaces:**
- Consumes: POST `asset_ids` comma-separated pks
- Produces: sets `is_archived=True`, `archived_at=now()` on those assets; they disappear from the batch list

- [ ] **Step 1: Write the failing test**

```python
class BatchArchiveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )
        self.client.post(
            "/scan/batch/save/",
            {"serial_number": "SN1", "mac_address": "aa:bb:cc:dd:ee:01", "skip_mac_2": "on"},
        )
        self.client.post(
            "/scan/batch/save/",
            {"serial_number": "SN2", "mac_address": "aa:bb:cc:dd:ee:02", "skip_mac_2": "on"},
        )

    def test_archive_one(self):
        a1 = Asset.objects.get(serial_number="SN1")
        self.client.post("/scan/batch/archive/", {"asset_ids": str(a1.pk)})
        a1.refresh_from_db()
        self.assertTrue(a1.is_archived)
        self.assertIsNotNone(a1.archived_at)
        home = self.client.get("/scan/batch/")
        self.assertNotContains(home, "SN1")
        self.assertContains(home, "SN2")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchArchiveTests -v 2`

Expected: FAIL — SN1 still visible / not archived

- [ ] **Step 3: Implement archive**

```python
@login_required
@require_POST
def batch_archive(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")
    ids = [int(x) for x in request.POST.get("asset_ids", "").split(",") if x.strip().isdigit()]
    Asset.objects.filter(pk__in=ids, site_name=site).update(
        is_archived=True, archived_at=timezone.now()
    )
    return redirect("scan:batch_home")
```

On `batch_home.html`, Archive posts hidden `asset_ids` from checked `.row-select` boxes (same pattern as `static/js/app.js` bulk form). If `app.js` already wires `[data-bulk-action]`, reuse it with `action="archive"` and `form` pointing at a POST form whose action is `{% url 'scan:batch_archive' %}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchArchiveTests -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/scan/batch.py templates/scan/batch_home.html apps/scan/tests/test_batch_scan.py
git commit -m "Archive selected devices from Batch Scan."
```

---

### Task 7: Batch report with serial and MAC barcodes

**Files:**
- Modify: `apps/assets/barcode_utils.py` — add `barcode_png_for_value(value: str) -> bytes` using Code 128 via existing `generate_1d_barcode_image`
- Modify: `apps/scan/batch.py` — implement `batch_report` and `_batch_target_assets(request)`
- Create: `templates/scan/batch_report.html`
- Test: `apps/scan/tests/test_batch_report_labels.py`

**Interfaces:**
- Consumes: `generate_1d_barcode_image(value, "code128")`
- Produces: `barcode_png_for_value(value: str) -> bytes`; `batch_report` GET `ids` optional comma list, else current batch (site + type, not archived); each row shows Code 128 for serial, MAC 1, and MAC 2 if present

- [ ] **Step 1: Write the failing test**

```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.assets.models import Asset

User = get_user_model()


class BatchReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )
        self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN1",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "mac_address_2": "aa:bb:cc:dd:ee:02",
            },
        )

    def test_report_includes_serial_and_mac_barcodes(self):
        response = self.client.get("/scan/batch/report/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")
        self.assertContains(response, "AA:BB:CC:DD:EE:02")
        self.assertContains(response, 'alt="SN1"')
        self.assertContains(response, 'alt="AA:BB:CC:DD:EE:01"')
        self.assertContains(response, 'alt="AA:BB:CC:DD:EE:02"')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_report_labels.BatchReportTests -v 2`

Expected: FAIL — redirect or missing barcode alts

- [ ] **Step 3: Implement barcode helper, queryset, report view and template**

Add to `apps/assets/barcode_utils.py`:

```python
import base64

def barcode_png_for_value(value: str) -> bytes:
    return generate_1d_barcode_image(value, "code128").getvalue()


def barcode_data_uri(value: str) -> str:
    png = barcode_png_for_value(value)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
```

In `apps/scan/batch.py`:

```python
from apps.assets.barcode_utils import barcode_data_uri


def batch_target_assets(request):
    key, meta, site, product = require_active_batch(request)
    if not site:
        return None, None, None, None, Asset.objects.none()
    ids_param = request.GET.get("ids") or request.POST.get("asset_ids") or ""
    ids = [int(x) for x in ids_param.split(",") if x.strip().isdigit()]
    qs = Asset.objects.filter(is_archived=False, site_name=site, product_name=product)
    if ids:
        qs = qs.filter(pk__in=ids)
    elif key:
        session_ids = request.session.get(key, [])
        qs = qs.filter(pk__in=session_ids)
    return key, meta, site, product, qs.order_by("created_at")


@login_required
def batch_report(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")
    key, meta, site, product, assets = batch_target_assets(request)
    if not site:
        return redirect("scan:batch_start")
    rows = []
    for asset in assets:
        rows.append(
            {
                "asset": asset,
                "serial_barcode": barcode_data_uri(asset.serial_number) if asset.serial_number else "",
                "mac_barcode": barcode_data_uri(asset.mac_address) if asset.mac_address else "",
                "mac2_barcode": barcode_data_uri(asset.mac_address_2) if asset.mac_address_2 else "",
            }
        )
    return render(
        request,
        "scan/batch_report.html",
        {"rows": rows, "site_name": site, "product_name": product, "total": len(rows)},
    )
```

`templates/scan/batch_report.html`: print toolbar (`window.print()`), table with site, type, serial, MACs, `created_at`, and `<img alt="{{ asset.serial_number }}" src="{{ row.serial_barcode }}">` plus MAC imgs. Use `class="no-print"` on the toolbar.

Wire Print report on `batch_home.html` to `{% url 'scan:batch_report' %}` (and append `?ids=` from selected boxes when any are checked).

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_report_labels.BatchReportTests -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/assets/barcode_utils.py apps/scan/batch.py templates/scan/batch_report.html templates/scan/batch_home.html apps/scan/tests/test_batch_report_labels.py
git commit -m "Add Batch Scan report with serial and MAC barcodes."
```

---

### Task 8: Device and per-value labels

**Files:**
- Modify: `apps/scan/batch.py` (`batch_labels`)
- Create: `templates/scan/batch_labels.html`
- Test: `apps/scan/tests/test_batch_report_labels.py`

**Interfaces:**
- Consumes: `batch_target_assets(request)`, `barcode_data_uri(value: str) -> str`
- Produces: GET `/scan/batch/labels/?mode=device|value` plus optional `ids`; `mode=device` one sticker per asset; `mode=value` one sticker per serial and each present MAC

- [ ] **Step 1: Write the failing tests**

```python
class BatchLabelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )
        self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN1",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "mac_address_2": "aa:bb:cc:dd:ee:02",
            },
        )

    def test_device_mode_one_label(self):
        response = self.client.get("/scan/batch/labels/?mode=device")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-label-count=\"1\"")
        self.assertContains(response, "SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")

    def test_value_mode_three_labels(self):
        response = self.client.get("/scan/batch/labels/?mode=value")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-label-count=\"3\"")
        self.assertContains(response, "SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")
        self.assertContains(response, "AA:BB:CC:DD:EE:02")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_report_labels.BatchLabelTests -v 2`

Expected: FAIL — redirect or missing `data-label-count`

- [ ] **Step 3: Implement labels**

```python
@login_required
def batch_labels(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")
    key, meta, site, product, assets = batch_target_assets(request)
    if not site:
        return redirect("scan:batch_start")
    mode = request.GET.get("mode", "device")
    labels = []
    if mode == "value":
        for asset in assets:
            if asset.serial_number:
                labels.append({"title": "Serial", "value": asset.serial_number, "barcode": barcode_data_uri(asset.serial_number)})
            if asset.mac_address:
                labels.append({"title": "MAC", "value": asset.mac_address, "barcode": barcode_data_uri(asset.mac_address)})
            if asset.mac_address_2:
                labels.append({"title": "MAC 2", "value": asset.mac_address_2, "barcode": barcode_data_uri(asset.mac_address_2)})
    else:
        for asset in assets:
            labels.append(
                {
                    "title": f"{asset.product_name} — {asset.site_name}",
                    "value": asset.serial_number,
                    "extra": " / ".join(m for m in (asset.mac_address, asset.mac_address_2) if m),
                    "barcode": barcode_data_uri(asset.serial_number) if asset.serial_number else "",
                    "mac_barcode": barcode_data_uri(asset.mac_address) if asset.mac_address else "",
                    "mac2_barcode": barcode_data_uri(asset.mac_address_2) if asset.mac_address_2 else "",
                }
            )
    return render(
        request,
        "scan/batch_labels.html",
        {"labels": labels, "mode": mode, "site_name": site, "product_name": product},
    )
```

`templates/scan/batch_labels.html`: wrap the sheet in `<div data-label-count="{{ labels|length }}">`. CSS: `.label-sheet { display:grid; grid-template-columns:repeat(2, 1fr); gap:0.5in; }` and `.label-sticker { border:1px solid #000; padding:0.25in; page-break-inside:avoid; }`. Print button. Device mode shows site/type/serial/MACs and barcode images; value mode shows title + value + one barcode.

On `batch_home.html` add two links/buttons: Print device labels → `/scan/batch/labels/?mode=device`, Print value labels → `/scan/batch/labels/?mode=value`, both appending selected `ids` when checked.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_report_labels.BatchLabelTests -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/scan/batch.py templates/scan/batch_labels.html templates/scan/batch_home.html apps/scan/tests/test_batch_report_labels.py
git commit -m "Print Batch Scan labels per device or per serial/MAC."
```

---

### Task 9: Show MACs on existing asset screens

**Files:**
- Modify: `apps/assets/views.py` (`asset_list` search `Q` includes `mac_address` and `mac_address_2`)
- Modify: `templates/assets/list.html` — Serial column stays; add MAC / MAC 2 columns
- Modify: `templates/assets/detail.html` — display both MACs
- Test: add `AssetListMacSearchTests` in `apps/assets/tests/test_asset_mac_uniqueness.py`

**Interfaces:**
- Consumes: `Asset.mac_address`, `Asset.mac_address_2`
- Produces: list search finds MAC; list/detail render MAC values

- [ ] **Step 1: Write the failing test**

```python
class AssetListMacSearchTests(TestCase):
    def setUp(self):
        User = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model()
        user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(user)
        Asset.objects.create(
            product_name="AP",
            site_name="HQ",
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:01",
            barcode_value="AT-MAC-SEARCH",
        )

    def test_search_by_mac(self):
        response = self.client.get("/assets/", {"q": "AA:BB:CC:DD:EE:01"})
        self.assertContains(response, "SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests.test_asset_mac_uniqueness.AssetListMacSearchTests -v 2`

Expected: FAIL — MAC not in list HTML and/or search miss

- [ ] **Step 3: Add search Q and template columns**

In `asset_list` filters add `| Q(mac_address__icontains=q) | Q(mac_address_2__icontains=q)`.

In `list.html` add `<th>MAC</th><th>MAC 2</th>` and cells. In `detail.html` add two definition rows for the MACs. Bump empty-row `colspan` by 2.

- [ ] **Step 4: Run full batch-related tests**

Run: `.\.venv\Scripts\python.exe manage.py test apps.assets.tests apps.scan.tests -v 2`

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add apps/assets/views.py templates/assets/list.html templates/assets/detail.html apps/assets/tests/test_asset_mac_uniqueness.py
git commit -m "Show and search asset MAC addresses on the assets list."
```

---

## Spec coverage check

| Spec item | Task |
|---|---|
| Batch Scan page, site + type, then SN/MACs | 3, 4, 5 |
| Skip 2nd MAC checkbox | 3, 4, 5 |
| Timestamp `created_at` | 5 |
| No duplicate serial (same site) / MAC (anywhere), no override | 2, 5 |
| Archive one or many | 6 |
| Report barcodes for serial + each MAC | 7 |
| Labels device + per value | 8 |
| Nav link | 4 |
| Existing `/scan/` unchanged | all (new URLs only) |
| Edit MACs via existing asset form | 3, 9 |
| Tests listed in spec | 1–8 |

No TBD/TODO placeholders. Names are consistent: `normalize_mac`, `StartBatchForm`, `BatchItemForm`, `batch_target_assets`, `barcode_data_uri`, session keys `batch_session_key` / `batch_sessions_meta`.
