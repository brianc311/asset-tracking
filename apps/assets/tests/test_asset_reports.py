from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.assets.barcode_utils import asset_report_table_data, assets_have_second_mac, assets_pdf_bytes
from apps.assets.models import Asset

User = get_user_model()


class AssetReportMacColumnsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.asset = Asset.objects.create(
            site_name="Test",
            product_name="Switches",
            serial_number="444444",
            mac_address="AA:BB:CC:DD:EE:01",
            barcode_value="AT-TESTMAC01",
            location="Room1",
        )

    def test_html_report_includes_mac_and_omits_empty_mac_2(self):
        response = self.client.get("/assets/report/", {"site": "Test"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<th>MAC</th>")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")
        self.assertNotContains(response, "<th>MAC 2</th>")

    def test_html_report_includes_mac_2_when_any_row_has_it(self):
        self.asset.mac_address_2 = "AA:BB:CC:DD:EE:02"
        self.asset.save(update_fields=["mac_address_2"])

        response = self.client.get("/assets/report/", {"site": "Test"})
        self.assertContains(response, "<th>MAC</th>")
        self.assertContains(response, "<th>MAC 2</th>")
        self.assertContains(response, "AA:BB:CC:DD:EE:02")

    def test_site_report_omits_empty_mac_2(self):
        response = self.client.get("/assets/reports/view/", {"site": "Test"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<th>MAC</th>")
        self.assertNotContains(response, "<th>MAC 2</th>")

    def test_pdf_omits_empty_mac_2_header(self):
        qs = Asset.objects.filter(pk=self.asset.pk)
        data, show_mac_2 = asset_report_table_data(qs)
        self.assertFalse(show_mac_2)
        self.assertIn("MAC", data[0])
        self.assertNotIn("MAC 2", data[0])
        mac_index = data[0].index("MAC")
        self.assertEqual(data[1][mac_index], "AA:BB:CC:DD:EE:01")
        pdf = assets_pdf_bytes(qs, title="Asset Report")
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_pdf_includes_mac_2_when_present(self):
        self.asset.mac_address_2 = "AA:BB:CC:DD:EE:02"
        self.asset.save(update_fields=["mac_address_2"])
        qs = Asset.objects.filter(pk=self.asset.pk)
        data, show_mac_2 = asset_report_table_data(qs)
        self.assertTrue(show_mac_2)
        self.assertIn("MAC 2", data[0])
        mac_2_index = data[0].index("MAC 2")
        self.assertEqual(data[1][mac_2_index], "AA:BB:CC:DD:EE:02")
        pdf = assets_pdf_bytes(qs, title="Asset Report")
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_assets_have_second_mac_false_for_empty_values(self):
        self.assertFalse(assets_have_second_mac(Asset.objects.all()))
        self.assertFalse(assets_have_second_mac([self.asset]))
