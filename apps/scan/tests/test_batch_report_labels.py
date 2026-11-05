from django.contrib.auth import get_user_model
from django.test import TestCase

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
