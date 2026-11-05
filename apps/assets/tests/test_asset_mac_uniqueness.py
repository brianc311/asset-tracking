from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.assets.models import Asset


def make_asset(**kwargs):
    defaults = {
        "product_name": "AP",
        "barcode_value": kwargs.pop(
            "barcode_value", f"AT-{kwargs.get('serial_number', 'X')}"
        ),
        "site_name": "SiteA",
        "serial_number": "SN1",
    }
    defaults.update(kwargs)
    return Asset.objects.create(**defaults)


class AssetMacUniquenessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="asset-test-user")

    def test_duplicate_serial_same_site_rejected(self):
        make_asset(serial_number="SN1", mac_address="AA:BB:CC:DD:EE:01")
        asset = Asset(
            product_name="AP",
            site_name="SiteA",
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:02",
            barcode_value="AT-DUP-SN",
            created_by=self.user,
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
            created_by=self.user,
        )
        asset.full_clean()

    def test_duplicate_mac_any_site_rejected(self):
        make_asset(
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:01",
            site_name="SiteA",
        )
        asset = Asset(
            product_name="Switch",
            site_name="SiteB",
            serial_number="SN9",
            mac_address="AA:BB:CC:DD:EE:01",
            barcode_value="AT-DUP-MAC",
            created_by=self.user,
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
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            asset.full_clean()

    def test_archived_serial_does_not_block(self):
        make_asset(
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:01",
            is_archived=True,
        )
        asset = Asset(
            product_name="AP",
            site_name="SiteA",
            serial_number="SN1",
            mac_address="AA:BB:CC:DD:EE:02",
            barcode_value="AT-REUSE",
            created_by=self.user,
        )
        asset.full_clean()
