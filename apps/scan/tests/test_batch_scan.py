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
