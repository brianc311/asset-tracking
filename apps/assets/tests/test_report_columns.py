from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.assets.barcode_utils import asset_report_table_data, assets_pdf_bytes
from apps.assets.models import Asset
from apps.assets.report_columns import (
    REPORT_COLUMN_KEYS,
    parse_report_columns,
    visible_report_columns,
)

User = get_user_model()


class ParseReportColumnsTests(SimpleTestCase):
    def test_blank_defaults_to_all(self):
        self.assertEqual(parse_report_columns(None), REPORT_COLUMN_KEYS)
        self.assertEqual(parse_report_columns(""), REPORT_COLUMN_KEYS)
        self.assertEqual(parse_report_columns("nope"), REPORT_COLUMN_KEYS)

    def test_filters_unknown_and_duplicates_and_keeps_canonical_order(self):
        self.assertEqual(
            parse_report_columns("mac,serial,mac,nope,device_name"),
            ("device_name", "serial", "mac"),
        )

    def test_hides_mac_2_when_empty_even_if_selected(self):
        keys = parse_report_columns("serial,mac,mac_2")
        self.assertEqual(visible_report_columns(keys, show_mac_2=False), ("serial", "mac"))
        self.assertEqual(visible_report_columns(keys, show_mac_2=True), ("serial", "mac", "mac_2"))

    def test_mac_2_only_selection_falls_back_when_empty(self):
        keys = visible_report_columns(("mac_2",), show_mac_2=False)

        self.assertTrue(keys)
        self.assertNotIn("mac_2", keys)


class ReportColumnPickerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.asset = Asset.objects.create(
            site_name="Test",
            product_name="Switches",
            device_name="EPS-Switch-01",
            serial_number="444444",
            mac_address="AA:BB:CC:DD:EE:01",
            barcode_value="AT-COLS01",
            model_number="SP4628",
            location="Room1",
        )

    def test_default_html_includes_device_name(self):
        response = self.client.get("/assets/report/", {"site": "Test"})
        self.assertContains(response, "<th>Device Name</th>")
        self.assertContains(response, "EPS-Switch-01")
        self.assertContains(response, 'name="cols"')

    def test_cols_query_hides_unselected_fields(self):
        response = self.client.get("/assets/report/", {"site": "Test", "cols": "serial,mac"})
        self.assertContains(response, "<th>Serial</th>")
        self.assertContains(response, "<th>MAC</th>")
        self.assertNotContains(response, "<th>Device Name</th>")
        self.assertNotContains(response, "<th>Location</th>")
        self.assertContains(response, 'href="?site=Test&amp;cols=serial,mac&amp;export=pdf"')

    def test_table_data_follows_selected_columns(self):
        data, _ = asset_report_table_data(
            Asset.objects.filter(pk=self.asset.pk),
            column_keys=("device_name", "serial"),
        )
        self.assertEqual(data[0], ["Device Name", "Serial"])
        self.assertEqual(data[1][0], "EPS-Switch-01")
        self.assertEqual(data[1][1], "444444")

    def test_pdf_falls_back_when_only_selected_mac_2_is_empty(self):
        pdf = assets_pdf_bytes(
            Asset.objects.filter(pk=self.asset.pk),
            title="Asset Report",
            column_keys=("mac_2",),
        )

        self.assertTrue(pdf.startswith(b"%PDF"))
