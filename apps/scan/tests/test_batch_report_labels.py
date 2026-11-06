from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.assets.models import Asset

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
        self.assertContains(response, 'alt="SN1"')
        self.assertContains(response, 'alt="AA:BB:CC:DD:EE:01"')
        self.assertContains(response, 'alt="AA:BB:CC:DD:EE:02"')

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
        self.assertContains(response, "SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")

    def test_value_mode_three_labels(self):
        response = self.client.get("/scan/batch/labels/?mode=value")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-label-count="3"')
        self.assertContains(response, "SN1")
        self.assertContains(response, "AA:BB:CC:DD:EE:01")
        self.assertContains(response, "AA:BB:CC:DD:EE:02")
