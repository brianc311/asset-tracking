# Full Batch Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Quick / Full switch on Batch Scan so Full can save Model and Location, remember the last values, and keep the current fast serial/MAC loop as Quick.

**Architecture:** Stay on the existing `Asset` model and batch session. Store `mode`, `last_model_number`, and `last_location` on `batch_sessions_meta` for the active key. Quick saves leave Model/Location blank; Full saves write those fields and seed the next form. GET `?mode=quick|full` updates session then redirects to `/scan/batch/`.

**Tech Stack:** Django 5, existing Batch Scan views/forms/templates, Django `TestCase` via `manage.py test`.

## Global Constraints

- Keep a single Batch Scan page and session — no second nav item, no new models.
- Quick is serial, MAC 1, optional MAC 2, Skip 2nd MAC. Full adds Model and Location only.
- Model and Location are optional even in Full.
- After a Full save, serial and MACs clear; Model and Location keep the last Full values.
- Quick save stores blank Model and Location and must not overwrite remembered Full values.
- Mode switch is GET `?mode=quick` or `?mode=full` on `/scan/batch/`, then redirect to `/scan/batch/` with no query string.
- Default mode is `quick`.
- Do not add comments, photo, asset number, or barcode type to Batch Scan.
- Do not change site reports, PDF columns, or labels for model/location.
- Staff+ only (`user.can_manage_assets()`), same as current Batch Scan.
- Run tests with: `.\.venv\Scripts\python.exe manage.py test <dotted.path> -v 2`

## File map

- Modify: `apps/scan/batch.py` — mode helpers, GET `?mode=`, Full/Quick save, remembered initial values
- Modify: `apps/scan/forms.py` — optional `model_number` and `location` on `BatchItemForm`
- Modify: `templates/scan/batch_home.html` — Quick/Full control, Full fields, Batch Items columns
- Modify: `apps/scan/tests/test_batch_scan.py` — mode, save, remember, UI, failed-redisplay tests

---

### Task 1: Persist Quick / Full mode on the batch session

**Files:**
- Modify: `apps/scan/batch.py`
- Test: `apps/scan/tests/test_batch_scan.py`

**Interfaces:**
- Consumes: existing `BATCH_META`, `BATCH_KEY`, `require_active_batch(request)`
- Produces: `MODE_QUICK = "quick"`, `MODE_FULL = "full"`, `normalize_batch_mode(raw) -> str`, `_update_batch_meta(request, key, **fields) -> dict`. `batch_home` GET `?mode=quick|full` writes `meta["mode"]` then redirects to `scan:batch_home`. Unknown `mode` values are ignored. New batches default to `quick`.

- [ ] **Step 1: Write the failing test**

Add this class to `apps/scan/tests/test_batch_scan.py` (keep existing tests):

```python
class BatchModeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )

    def _meta(self):
        session = self.client.session
        key = session["batch_session_key"]
        return session["batch_sessions_meta"][key]

    def test_new_batch_defaults_to_quick(self):
        self.assertEqual(self._meta().get("mode", "quick"), "quick")

    def test_mode_query_persists_on_refresh(self):
        response = self.client.get("/scan/batch/", {"mode": "full"})
        self.assertRedirects(response, "/scan/batch/")
        self.assertEqual(self._meta()["mode"], "full")
        self.client.get("/scan/batch/")
        self.assertEqual(self._meta()["mode"], "full")

    def test_invalid_mode_query_is_ignored(self):
        self.client.get("/scan/batch/", {"mode": "full"})
        self.client.get("/scan/batch/", {"mode": "nope"})
        self.assertEqual(self._meta()["mode"], "full")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchModeTests -v 2`

Expected: FAIL — `test_mode_query_persists_on_refresh` 200 != 302 (home currently ignores `mode` and renders 200)

- [ ] **Step 3: Write minimal implementation**

In `apps/scan/batch.py`, add helpers after `BATCH_META` and use them in `batch_start` / `batch_home`:

```python
MODE_QUICK = "quick"
MODE_FULL = "full"


def normalize_batch_mode(raw) -> str:
    return MODE_FULL if (raw or "").strip().lower() == MODE_FULL else MODE_QUICK


def _update_batch_meta(request, key, **fields):
    all_meta = dict(request.session.get(BATCH_META, {}))
    current = dict(all_meta.get(key) or {})
    current.update(fields)
    all_meta[key] = current
    request.session[BATCH_META] = all_meta
    request.session.modified = True
    return current
```

In `batch_start`, when creating `meta[key]`, include:

```python
"mode": MODE_QUICK,
"last_model_number": "",
"last_location": "",
```

At the top of `batch_home`, after `require_active_batch` succeeds:

```python
requested = (request.GET.get("mode") or "").strip().lower()
if requested in (MODE_QUICK, MODE_FULL):
    _update_batch_meta(request, key, mode=requested)
    return redirect("scan:batch_home")
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchModeTests apps.scan.tests.test_batch_scan.BatchViewTests -v 2`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/scan/batch.py apps/scan/tests/test_batch_scan.py
git commit -m "Remember Quick or Full Batch Scan mode on the current session."
```

---

### Task 2: Save Model and Location only in Full mode

**Files:**
- Modify: `apps/scan/forms.py`
- Modify: `apps/scan/batch.py`
- Test: `apps/scan/tests/test_batch_scan.py`

**Interfaces:**
- Consumes: `normalize_batch_mode`, `_update_batch_meta`, `MODE_FULL`, `MODE_QUICK`
- Produces: `BatchItemForm` fields `model_number` (`max_length=128`, required=False) and `location` (`max_length=255`, required=False). `batch_save` writes those onto `Asset` only when session mode is `full`; otherwise stores `""`. After a successful Full save, updates `last_model_number` and `last_location`. Quick save does not change those remembered keys.

- [ ] **Step 1: Write the failing test**

Add to `apps/scan/tests/test_batch_scan.py`:

```python
class BatchFullSaveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )

    def _meta(self):
        session = self.client.session
        key = session["batch_session_key"]
        return session["batch_sessions_meta"][key]

    def test_full_save_stores_model_and_location(self):
        self.client.get("/scan/batch/", {"mode": "full"})
        response = self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN-FULL",
                "mac_address": "aa:bb:cc:dd:ee:11",
                "model_number": "SP4628",
                "location": "Room1",
            },
        )
        self.assertRedirects(response, "/scan/batch/")
        asset = Asset.objects.get(serial_number="SN-FULL")
        self.assertEqual(asset.model_number, "SP4628")
        self.assertEqual(asset.location, "Room1")
        self.assertEqual(self._meta()["last_model_number"], "SP4628")
        self.assertEqual(self._meta()["last_location"], "Room1")

    def test_quick_save_ignores_posted_model_and_location(self):
        self.client.get("/scan/batch/", {"mode": "full"})
        self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN-FULL",
                "mac_address": "aa:bb:cc:dd:ee:11",
                "model_number": "SP4628",
                "location": "Room1",
            },
        )
        self.client.get("/scan/batch/", {"mode": "quick"})
        response = self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN-QUICK",
                "mac_address": "aa:bb:cc:dd:ee:22",
                "model_number": "SHOULD-IGNORE",
                "location": "SHOULD-IGNORE",
            },
        )
        self.assertRedirects(response, "/scan/batch/")
        asset = Asset.objects.get(serial_number="SN-QUICK")
        self.assertEqual(asset.model_number, "")
        self.assertEqual(asset.location, "")
        self.assertEqual(self._meta()["last_model_number"], "SP4628")
        self.assertEqual(self._meta()["last_location"], "Room1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchFullSaveTests -v 2`

Expected: FAIL — `asset.model_number` is `""` because `batch_save` does not set it

- [ ] **Step 3: Write minimal implementation**

Add fields to `BatchItemForm` in `apps/scan/forms.py` after `skip_mac_2`:

```python
    model_number = forms.CharField(
        required=False,
        max_length=128,
        widget=forms.TextInput(
            attrs={"class": "form-input", "id": "id_model_number", "placeholder": "Model number"}
        ),
    )
    location = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-input", "id": "id_location", "placeholder": "Room, shelf, or specific spot"}
        ),
    )
```

In `batch_save`, after `form.is_valid()`, derive values from session mode (not from “fields happened to be posted”):

```python
        mode = normalize_batch_mode(meta.get("mode"))
        if mode == MODE_FULL:
            model_number = (form.cleaned_data.get("model_number") or "").strip()
            location = (form.cleaned_data.get("location") or "").strip()
        else:
            model_number = ""
            location = ""
        asset = Asset(
            site_name=site,
            product_name=product,
            serial_number=form.cleaned_data["serial_number"].strip(),
            mac_address=form.cleaned_data["mac_address"],
            mac_address_2=form.cleaned_data["mac_address_2"],
            model_number=model_number,
            location=location,
            barcode_value=Asset.generate_barcode_value(),
            created_by=request.user,
            updated_by=request.user,
        )
```

In the successful-save `else` branch, before redirect:

```python
            if mode == MODE_FULL:
                _update_batch_meta(
                    request,
                    key,
                    last_model_number=model_number,
                    last_location=location,
                )
```

Keep appending the asset id to the session list as today.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchFullSaveTests apps.scan.tests.test_batch_scan.BatchSaveTests -v 2`

Expected: PASS (existing Quick saves still work; they post no model/location and stay in default quick)

- [ ] **Step 5: Commit**

```bash
git add apps/scan/forms.py apps/scan/batch.py apps/scan/tests/test_batch_scan.py
git commit -m "Save model and location from Full Batch Scan without changing Quick saves."
```

---

### Task 3: Full form UI, remembered values, and Batch Items columns

**Files:**
- Modify: `apps/scan/batch.py`
- Modify: `templates/scan/batch_home.html`
- Test: `apps/scan/tests/test_batch_scan.py`

**Interfaces:**
- Consumes: `normalize_batch_mode`, `MODE_FULL`, `MODE_QUICK`, `meta["last_model_number"]`, `meta["last_location"]`
- Produces: `batch_home` and failed `batch_save` render `batch_mode` and, in Full, a `BatchItemForm(initial={model_number, location})` from remembered values. Template shows Quick/Full links, Full-only Model/Location rows with Scan buttons, and Batch Items columns for Model and Location.

- [ ] **Step 1: Write the failing test**

Add to `apps/scan/tests/test_batch_scan.py`:

```python
class BatchFullUiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )

    def test_quick_hides_model_and_location_fields(self):
        home = self.client.get("/scan/batch/")
        self.assertContains(home, ">Quick</a>")
        self.assertContains(home, ">Full</a>")
        self.assertNotContains(home, 'id="id_model_number"')
        self.assertNotContains(home, 'id="id_location"')

    def test_full_shows_model_and_location_and_keeps_them_after_save(self):
        self.client.get("/scan/batch/", {"mode": "full"})
        self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN-FULL",
                "mac_address": "aa:bb:cc:dd:ee:11",
                "model_number": "SP4628",
                "location": "Room1",
            },
        )
        home = self.client.get("/scan/batch/")
        self.assertContains(home, 'id="id_model_number"')
        self.assertContains(home, 'value="SP4628"')
        self.assertContains(home, 'value="Room1"')
        self.assertNotContains(home, 'value="SN-FULL"')
        self.assertNotContains(home, "AA:BB:CC:DD:EE:11")
        self.assertContains(home, "<th>Model</th>")
        self.assertContains(home, "<th>Location</th>")
        self.assertContains(home, "SP4628")
        self.assertContains(home, "Room1")

    def test_failed_full_save_keeps_posted_model_and_location(self):
        Asset.objects.create(
            product_name="AP",
            site_name="HQ",
            serial_number="SN-DUP",
            mac_address="AA:BB:CC:DD:EE:99",
            barcode_value="AT-EXIST-FULL",
        )
        self.client.get("/scan/batch/", {"mode": "full"})
        response = self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN-DUP",
                "mac_address": "aa:bb:cc:dd:ee:33",
                "model_number": "SP4628",
                "location": "Room2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This serial number is already in the database.")
        self.assertContains(response, 'value="SP4628"')
        self.assertContains(response, 'value="Room2"')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan.BatchFullUiTests -v 2`

Expected: FAIL — home HTML has no Quick/Full links and no `id_model_number`

- [ ] **Step 3: Write minimal implementation**

In `apps/scan/batch.py`, add a shared renderer and use it from `batch_home` and the failed-save path in `batch_save`:

```python
def _batch_form(meta, data=None):
    mode = normalize_batch_mode(meta.get("mode"))
    if data is not None:
        return BatchItemForm(data)
    initial = {}
    if mode == MODE_FULL:
        initial = {
            "model_number": meta.get("last_model_number") or "",
            "location": meta.get("last_location") or "",
        }
    return BatchItemForm(initial=initial)


def _render_batch_home(request, key, meta, site, product, form, status=200):
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
            "batch_mode": normalize_batch_mode(meta.get("mode")),
        },
        status=status,
    )
```

`batch_home` after handling `?mode=` should end with:

```python
    return _render_batch_home(request, key, meta, site, product, _batch_form(meta))
```

`batch_save` failed path (form invalid or `ValidationError`) should return:

```python
    return _render_batch_home(request, key, meta, site, product, form, status=200)
```

Do not build a new empty form on failed save — keep the bound `form` so posted Model/Location remain.

In `templates/scan/batch_home.html`, put this immediately inside the scan card, above the save `<form>`:

```html
  <div class="toolbar" style="margin-bottom:1rem">
    <a href="?mode=quick" class="btn {% if batch_mode != 'full' %}btn-primary{% else %}btn-secondary{% endif %}">Quick</a>
    <a href="?mode=full" class="btn {% if batch_mode == 'full' %}btn-primary{% else %}btn-secondary{% endif %}">Full</a>
  </div>
```

After the Skip 2nd MAC row, before Save Asset, add Full-only fields:

```html
    {% if batch_mode == 'full' %}
    <div class="field-row">
      <label class="form-label" for="{{ form.model_number.id_for_label }}">Model</label>
      <div class="field-row-scan">
        {{ form.model_number }}
        <button type="button" class="btn btn-secondary btn-scan-field" data-scan-target="{{ form.model_number.id_for_label }}" data-scan-label="Model">📷 Scan</button>
      </div>
      {% if form.model_number.errors %}<p class="form-error" style="color:var(--danger);font-size:0.875rem">{{ form.model_number.errors.0 }}</p>{% endif %}
    </div>
    <div class="field-row">
      <label class="form-label" for="{{ form.location.id_for_label }}">Location</label>
      <div class="field-row-scan">
        {{ form.location }}
        <button type="button" class="btn btn-secondary btn-scan-field" data-scan-target="{{ form.location.id_for_label }}" data-scan-label="Location">📷 Scan</button>
      </div>
      {% if form.location.errors %}<p class="form-error" style="color:var(--danger);font-size:0.875rem">{{ form.location.errors.0 }}</p>{% endif %}
    </div>
    {% endif %}
```

Update Batch Items header, rows, and empty colspan:

```html
        <thead><tr><th>Select</th><th>#</th><th>Serial</th><th>MAC 1</th><th>MAC 2</th><th>Model</th><th>Location</th></tr></thead>
        <tbody>
          {% for asset in assets %}
          <tr>
            <td><input type="checkbox" class="row-select" value="{{ asset.pk }}"></td>
            <td>{{ asset.asset_number|default:"—" }}</td>
            <td>{{ asset.serial_number|default:"—" }}</td>
            <td>{{ asset.mac_address|default:"—" }}</td>
            <td>{{ asset.mac_address_2|default:"—" }}</td>
            <td>{{ asset.model_number|default:"—" }}</td>
            <td>{{ asset.location|default:"—" }}</td>
          </tr>
          {% empty %}
          <tr><td colspan="7" style="text-align:center;color:var(--text-muted)">No assets in this batch yet.</td></tr>
          {% endfor %}
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_scan -v 2`

Expected: PASS (all classes in this file, including prior Batch Scan tests)

Then: `.\.venv\Scripts\python.exe manage.py test apps.scan.tests.test_batch_report_labels -v 2`

Expected: PASS (report/label pages unchanged)

- [ ] **Step 5: Commit**

```bash
git add apps/scan/batch.py templates/scan/batch_home.html apps/scan/tests/test_batch_scan.py
git commit -m "Show Full Batch Scan fields and remember the last model and location."
```

---

## Spec coverage

- Single page Quick/Full switch — Task 1 (session) + Task 3 (links)
- GET `?mode=` then redirect, survives refresh — Task 1
- Default quick — Task 1
- Full save writes Model and Location — Task 2
- Quick save blank Model/Location — Task 2
- Quick save does not overwrite remembered values — Task 2
- After Full save, form keeps last Model/Location and clears serial/MAC — Task 3
- Batch Items Model/Location columns — Task 3
- Failed Full save redisplays posted Model/Location — Task 3
- Optional Model/Location — Task 2 (required=False)
- Scan buttons on Model/Location — Task 3
- Out of scope (comments/photo/reports/labels) — no tasks
