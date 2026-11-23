import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import BlockedIP
from apps.assets.models import Asset

User = get_user_model()


class SecurityDataBackupTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="boss",
            password="x",
            role=User.Role.SUPER_USER,
        )
        self.staff = User.objects.create_user(
            username="staff",
            password="x",
            role=User.Role.STAFF,
        )
        self.client.force_login(self.admin)
        self.asset = Asset.objects.create(
            product_name="Switches",
            site_name="HQ",
            barcode_value="AT-KEEP01",
            serial_number="SN-KEEP",
            location="Room1",
        )
        BlockedIP.objects.create(ip_address="10.1.1.1", reason="probe", blocked_by=self.admin)

    def test_security_page_has_import_and_export(self):
        response = self.client.get(reverse("accounts:security_logs"))
        self.assertContains(response, "Export data")
        self.assertContains(response, "Import data")

    def test_staff_cannot_export(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("accounts:export_data"))
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_export_includes_assets_and_blocked_ips(self):
        response = self.client.get(reverse("accounts:export_data"))
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["format"], "asset-tracking-backup")
        barcodes = [row["barcode_value"] for row in payload["assets"]]
        self.assertIn("AT-KEEP01", barcodes)
        ips = [row["ip_address"] for row in payload["blocked_ips"]]
        self.assertIn("10.1.1.1", ips)

    def test_import_adds_new_rows_and_skips_existing(self):
        payload = {
            "format": "asset-tracking-backup",
            "version": 1,
            "assets": [
                {
                    "barcode_value": "AT-KEEP01",
                    "product_name": "Should Not Overwrite",
                    "site_name": "Other",
                    "serial_number": "SN-KEEP",
                    "location": "Changed",
                },
                {
                    "barcode_value": "AT-NEW001",
                    "product_name": "Camera",
                    "site_name": "Plant",
                    "serial_number": "SN-NEW",
                    "location": "Dock",
                },
            ],
            "blocked_ips": [
                {"ip_address": "10.1.1.1", "reason": "changed", "is_active": True},
                {"ip_address": "10.9.9.9", "reason": "new block", "is_active": True},
            ],
        }
        upload = SimpleUploadedFile(
            "backup.json",
            json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )
        response = self.client.post(
            reverse("accounts:import_data"),
            {"backup_file": upload},
            follow=True,
        )
        self.assertContains(response, "Added 1 asset")
        self.assertContains(response, "skipped 1 existing")
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.product_name, "Switches")
        self.assertEqual(self.asset.location, "Room1")
        self.assertTrue(Asset.objects.filter(barcode_value="AT-NEW001", product_name="Camera").exists())
        existing_ip = BlockedIP.objects.get(ip_address="10.1.1.1")
        self.assertEqual(existing_ip.reason, "probe")
        self.assertTrue(BlockedIP.objects.filter(ip_address="10.9.9.9").exists())
