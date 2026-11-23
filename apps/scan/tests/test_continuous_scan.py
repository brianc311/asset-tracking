from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.assets.models import Asset
from apps.scan.continuous import classify_scan_value, find_duplicate

User = get_user_model()


class ContinuousScanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)
        self.client.post(
            "/scan/batch/start/",
            {
                "site_name": "__new__",
                "new_site_name": "HQ",
                "product_name": "__new__",
                "new_product_name": "AP",
            },
        )

    def test_classify_mac_vs_serial(self):
        kind, value = classify_scan_value("aa-bb-cc-dd-ee-01")
        self.assertEqual(kind, "mac")
        self.assertEqual(value, "AA:BB:CC:DD:EE:01")
        kind, value = classify_scan_value("SN-444444")
        self.assertEqual(kind, "serial")
        self.assertEqual(value, "SN-444444")

    def test_continuous_tab_loads(self):
        response = self.client.get("/scan/batch/", {"mode": "continuous"})
        self.assertRedirects(response, "/scan/batch/")
        home = self.client.get("/scan/batch/")
        self.assertContains(home, "Continuous Batch Scan")
        self.assertContains(home, "Export CSV")
        self.assertContains(home, "Export Excel")
        self.assertContains(home, "📷 Scan")
        self.assertContains(home, "html5-qrcode")
        self.assertContains(home, "continuous-scan")

    def test_done_shows_finish_fields(self):
        self.client.post("/scan/batch/continuous/add/", {"value": "SN-DONE"})
        response = self.client.post("/scan/batch/continuous/done/", follow=True)
        self.assertContains(response, "Finish this batch")
        self.assertContains(response, "Device Name")
        self.assertContains(response, "Serial number")
        self.assertContains(response, "MAC address")
        self.assertContains(response, "Location")
        self.assertContains(response, "Comments")
        self.assertContains(response, "Finish")

    def test_add_scan_and_session_duplicate(self):
        first = self.client.post("/scan/batch/continuous/add/", {"value": "SN-1"})
        self.assertEqual(first.json()["row"]["n"], 1)
        self.assertFalse(first.json()["row"]["duplicate"])
        second = self.client.post("/scan/batch/continuous/add/", {"value": "SN-1"})
        self.assertTrue(second.json()["row"]["duplicate"])
        self.assertIn("row 1", second.json()["row"]["duplicate_reason"])

    def test_database_duplicate_is_flagged(self):
        Asset.objects.create(
            product_name="AP",
            site_name="HQ",
            barcode_value="AT-EXIST1",
            serial_number="SN-DB",
            mac_address="AA:BB:CC:DD:EE:09",
        )
        response = self.client.post("/scan/batch/continuous/add/", {"value": "SN-DB"})
        self.assertTrue(response.json()["row"]["duplicate"])
        self.assertIn("database", response.json()["row"]["duplicate_reason"].lower())

    def test_finish_saves_new_rows_and_skips_duplicates(self):
        self.client.post("/scan/batch/continuous/add/", {"value": "SN-NEW"})
        self.client.post("/scan/batch/continuous/add/", {"value": "SN-NEW"})
        response = self.client.post(
            "/scan/batch/continuous/finish/",
            {"device_name": "AP-01", "location": "Room1", "comments": "batch", "model_number": "M1"},
            follow=True,
        )
        self.assertContains(response, "Saved 1 asset")
        asset = Asset.objects.get(serial_number="SN-NEW")
        self.assertEqual(asset.device_name, "AP-01")
        self.assertEqual(asset.location, "Room1")
        self.assertEqual(asset.comments, "batch")
        self.assertEqual(Asset.objects.filter(serial_number="SN-NEW").count(), 1)

    def test_csv_export_includes_rows(self):
        self.client.post("/scan/batch/continuous/add/", {"value": "SN-CSV"})
        response = self.client.get("/scan/batch/continuous/export.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn(b"SN-CSV", response.content)

    def test_excel_export_includes_rows(self):
        self.client.post("/scan/batch/continuous/add/", {"value": "SN-XLS"})
        response = self.client.get("/scan/batch/continuous/export.xls")
        self.assertEqual(response.status_code, 200)
        self.assertIn("excel", response["Content-Type"])
        self.assertIn(b"SN-XLS", response.content)

    def test_mac_duplicate_names_row(self):
        self.client.post("/scan/batch/continuous/add/", {"value": "aa:bb:cc:dd:ee:01"})
        second = self.client.post("/scan/batch/continuous/add/", {"value": "AA-BB-CC-DD-EE-01"})
        self.assertTrue(second.json()["row"]["duplicate"])
        self.assertIn("row 1", second.json()["row"]["duplicate_reason"])

    def test_finish_typed_serial_is_saved(self):
        self.client.post("/scan/batch/continuous/add/", {"value": "SN-CAM"})
        self.client.post(
            "/scan/batch/continuous/finish/",
            {
                "device_name": "AP-02",
                "serial_number": "SN-TYPED",
                "location": "Closet",
                "comments": "typed extra",
            },
            follow=True,
        )
        typed = Asset.objects.get(serial_number="SN-TYPED")
        self.assertEqual(typed.device_name, "AP-02")
        self.assertEqual(typed.location, "Closet")
        self.assertEqual(Asset.objects.filter(serial_number="SN-CAM").count(), 1)

    def test_find_duplicate_helper(self):
        rows = [{"n": 1, "serial": "ABC", "mac": ""}]
        dup = find_duplicate(rows, "serial", "abc", site_name="HQ")
        self.assertEqual(dup["row"], 1)
