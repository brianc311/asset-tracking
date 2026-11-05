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
