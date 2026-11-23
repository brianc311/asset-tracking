from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.assets.models import Asset
from apps.assets.site_names import NEW_SITE_VALUE

User = get_user_model()


class AssetCreateStayTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="staff",
            password="x",
            role=User.Role.STAFF,
        )
        self.client.force_login(user)

    def test_save_stays_on_create_form(self):
        response = self.client.post(
            "/assets/new/",
            {
                "site_name": NEW_SITE_VALUE,
                "new_site_name": "HQ",
                "product_name": "Switches",
                "serial_number": "444444",
                "mac_address": "1A-23-7G-4E-12-9A",
                "location": "Room1",
                "barcode_type": "qr",
            },
            follow=True,
        )
        self.assertEqual(Asset.objects.count(), 1)
        self.assertContains(response, "Saved Switches (444444). You can add another.")
        self.assertContains(response, "Save and add another")
        self.assertContains(response, "HQ")
        self.assertContains(response, "Switches")
        self.assertContains(response, "Room1")
        self.assertNotContains(response, 'value="444444"')
        self.assertNotContains(response, "1A:23:7G:4E:12:9A")


class AssetDeviceNameTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)

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
