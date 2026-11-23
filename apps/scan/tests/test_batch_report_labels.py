from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.assets.models import Asset
from apps.scan.label_fields import DEFAULT_LABEL_FIELDS, parse_label_fields

User = get_user_model()


class BatchReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )
        self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN1",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "mac_address_2": "aa:bb:cc:dd:ee:02",
            },
        )

    def test_report_includes_serial_and_mac_barcodes(self):
        response = self.client.get("/scan/batch/report/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")
        self.assertContains(response, "AA:BB:CC:DD:EE:02")
        self.assertContains(response, "<th>MAC</th>")
        self.assertContains(response, "<th>MAC 2</th>")
        self.assertContains(response, 'alt="SN1"')
        self.assertContains(response, 'alt="AA:BB:CC:DD:EE:01"')
        self.assertContains(response, 'alt="AA:BB:CC:DD:EE:02"')

    def test_report_omits_mac_2_column_when_empty(self):
        Asset.objects.filter(serial_number="SN1").update(mac_address_2="")
        response = self.client.get("/scan/batch/report/")
        self.assertContains(response, "<th>MAC</th>")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")
        self.assertNotContains(response, "MAC 2")

    def test_report_without_ids_includes_all_matching_active_assets(self):
        Asset.objects.create(
            site_name="HQ",
            product_name="AP",
            serial_number="SN-OLDER",
            barcode_value="AT-OLDER",
        )
        Asset.objects.create(
            site_name="HQ",
            product_name="Switch",
            serial_number="SN-WRONG-TYPE",
            barcode_value="AT-WRONG-TYPE",
        )
        Asset.objects.create(
            site_name="HQ",
            product_name="AP",
            serial_number="SN-ARCHIVED",
            barcode_value="AT-ARCHIVED",
            is_archived=True,
        )

        response = self.client.get("/scan/batch/report/")

        self.assertContains(response, "SN1")
        self.assertContains(response, "SN-OLDER")
        self.assertNotContains(response, "SN-WRONG-TYPE")
        self.assertNotContains(response, "SN-ARCHIVED")

    def test_report_ids_filter_matching_assets(self):
        selected = Asset.objects.create(
            site_name="HQ",
            product_name="AP",
            serial_number="SN-SELECTED",
            barcode_value="AT-SELECTED",
        )

        response = self.client.get("/scan/batch/report/", {"ids": str(selected.pk)})

        self.assertContains(response, "SN-SELECTED")
        self.assertNotContains(response, "SN1")

    def test_report_pdf_download(self):
        response = self.client.get("/scan/batch/report/", {"export": "pdf"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("attachment;", response["Content-Disposition"])

    def test_report_page_links_to_pdf_download(self):
        response = self.client.get("/scan/batch/report/")

        self.assertContains(response, "?export=pdf")


class BatchLabelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {"site_name": "__new__", "new_site_name": "HQ", "product_name": "__new__", "new_product_name": "AP"},
        )
        self.client.post(
            "/scan/batch/save/",
            {
                "serial_number": "SN1",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "mac_address_2": "aa:bb:cc:dd:ee:02",
            },
        )

    def test_device_mode_one_label(self):
        response = self.client.get("/scan/batch/labels/?mode=device")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-label-count="1"')
        self.assertContains(response, "Serial: SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")

    def test_device_mode_labels_serial_when_device_name_is_blank(self):
        response = self.client.get("/scan/batch/labels/?mode=device")
        self.assertContains(response, "Serial: SN1")
        self.assertNotContains(response, '<div class="label-value">SN1</div>')

    def test_value_mode_three_labels(self):
        response = self.client.get("/scan/batch/labels/?mode=value")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-label-count="3"')
        self.assertContains(response, "SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")
        self.assertContains(response, "AA:BB:CC:DD:EE:02")
        self.assertNotContains(response, 'name="field"')

    def test_device_mode_prints_device_name_as_main_line(self):
        Asset.objects.filter(serial_number="SN1").update(device_name="EPS-AP-01")
        response = self.client.get("/scan/batch/labels/?mode=device")
        self.assertContains(response, "EPS-AP-01")
        self.assertContains(response, "SN1")
        self.assertContains(response, 'name="field"')

    def test_device_mode_fields_query_adds_selected_extra_lines(self):
        Asset.objects.filter(serial_number="SN1").update(
            device_name="EPS-AP-01",
            location="Room 12",
            model_number="SP4628",
        )
        response = self.client.get("/scan/batch/labels/", {"mode": "device", "fields": "location,model"})
        self.assertContains(response, "Location: Room 12")
        self.assertContains(response, "Model: SP4628")
        self.assertNotContains(response, "Serial: SN1")
        self.assertContains(response, 'alt="SN1"')

    def test_device_mode_empty_fields_omits_extra_text(self):
        Asset.objects.filter(serial_number="SN1").update(device_name="EPS-AP-01")
        response = self.client.get("/scan/batch/labels/", {"mode": "device", "fields": ""})
        self.assertContains(response, "EPS-AP-01")
        self.assertNotContains(response, "Serial: SN1")
        self.assertNotContains(response, "MAC: AA:BB:CC:DD:EE:01")


class ParseLabelFieldsTests(SimpleTestCase):
    def test_missing_defaults_to_serial_and_macs(self):
        self.assertEqual(parse_label_fields(None), DEFAULT_LABEL_FIELDS)

    def test_empty_means_no_extra_fields(self):
        self.assertEqual(parse_label_fields(""), ())

    def test_filters_unknown_and_keeps_canonical_order(self):
        self.assertEqual(
            parse_label_fields("location,serial,location,nope,mac"),
            ("serial", "mac", "location"),
        )
