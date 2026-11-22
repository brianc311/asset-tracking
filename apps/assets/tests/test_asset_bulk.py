from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.assets.models import Asset
from apps.assets.product_types import NEW_PRODUCT_VALUE
from apps.assets.site_names import NEW_SITE_VALUE

User = get_user_model()


class AssetBulkUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.a1 = Asset.objects.create(
            product_name="AP",
            site_name="HQ",
            barcode_value="AT-BULK01",
            serial_number="SN1",
            location="Room1",
        )
        self.a2 = Asset.objects.create(
            product_name="AP",
            site_name="HQ",
            barcode_value="AT-BULK02",
            serial_number="SN2",
            location="Room2",
        )

    def _post(self, **extra):
        data = {
            "action": "update",
            "asset_ids": f"{self.a1.pk},{self.a2.pk}",
            **extra,
        }
        return self.client.post(reverse("assets:bulk"), data, follow=True)

    def test_list_has_update_selected(self):
        response = self.client.get(reverse("assets:list"))
        self.assertContains(response, "Update selected")
        self.assertContains(response, 'name="field"')

    def test_bulk_updates_product_name(self):
        response = self._post(field="product_name", product_name="Switches")
        self.assertEqual(response.status_code, 200)
        self.a1.refresh_from_db()
        self.a2.refresh_from_db()
        self.assertEqual(self.a1.product_name, "Switches")
        self.assertEqual(self.a2.product_name, "Switches")
        self.assertContains(response, "Updated Product")

    def test_bulk_updates_product_name_with_new_type(self):
        self._post(field="product_name", product_name=NEW_PRODUCT_VALUE, new_product_name="Camera")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.product_name, "Camera")

    def test_bulk_product_requires_a_type(self):
        self._post(field="product_name", product_name="")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.product_name, "AP")

    def test_bulk_updates_site_name(self):
        self._post(field="site_name", site_name="Warehouse")
        self.a1.refresh_from_db()
        self.a2.refresh_from_db()
        self.assertEqual(self.a1.site_name, "Warehouse")
        self.assertEqual(self.a2.site_name, "Warehouse")

    def test_bulk_updates_site_with_new_name(self):
        self._post(field="site_name", site_name=NEW_SITE_VALUE, new_site_name="Plant 2")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.site_name, "Plant 2")

    def test_bulk_updates_location(self):
        self._post(field="location", value="Closet A")
        self.a1.refresh_from_db()
        self.a2.refresh_from_db()
        self.assertEqual(self.a1.location, "Closet A")
        self.assertEqual(self.a2.location, "Closet A")

    def test_bulk_clears_location_when_blank(self):
        self._post(field="location", value="")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.location, "")

    def test_archive_still_works(self):
        self.client.post(
            reverse("assets:bulk"),
            {"action": "archive", "asset_ids": str(self.a1.pk)},
        )
        self.a1.refresh_from_db()
        self.assertTrue(self.a1.is_archived)

    def test_readonly_user_cannot_bulk_update(self):
        viewer = User.objects.create_user(username="viewer", password="x", role=User.Role.USER)
        self.client.force_login(viewer)
        self._post(field="product_name", product_name="Switches")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.product_name, "AP")
