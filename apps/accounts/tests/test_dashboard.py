from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.assets.models import Asset

User = get_user_model()


class DashboardRecentlyAddedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)

    def test_recently_added_shows_site_name(self):
        Asset.objects.create(
            product_name="Switches",
            site_name="Test",
            barcode_value="AT-DASH01",
            serial_number="SN1",
        )
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertContains(response, "Recently Added")
        self.assertContains(response, "<th>Site</th>", html=True)
        self.assertContains(response, "Test")
