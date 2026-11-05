from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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

    def test_non_staff_user_cannot_access_batch_views(self):
        user = User.objects.create_user(username="user", password="x", role=User.Role.USER)
        self.client.force_login(user)

        start_response = self.client.get("/scan/batch/start/")
        end_response = self.client.post("/scan/batch/end/")

        dashboard_url = reverse("accounts:dashboard")
        self.assertRedirects(start_response, dashboard_url)
        self.assertRedirects(end_response, dashboard_url)


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
        asset = Asset.objects.get(serial_number="SN1")

        self.client.post("/scan/batch/archive/", {"asset_ids": str(asset.pk)})

        asset.refresh_from_db()
        self.assertTrue(asset.is_archived)
        self.assertIsNotNone(asset.archived_at)
        home = self.client.get("/scan/batch/")
        self.assertNotContains(home, "SN1")
        self.assertContains(home, "SN2")
