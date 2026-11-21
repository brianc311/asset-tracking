from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.assets.barcode_utils import generate_qr_image
from apps.assets.models import Asset

User = get_user_model()


class AssetBarcodeToggleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="staff",
            password="x",
            role=User.Role.STAFF,
        )
        self.client.force_login(self.user)
        self.asset = Asset.objects.create(
            product_name="Switches",
            barcode_value="AT-QRTOGGLE01",
            barcode_type=Asset.BarcodeType.QR,
        )

    def test_detail_page_has_asset_and_website_qr_toggle(self):
        response = self.client.get(reverse("assets:detail", args=[self.asset.pk]))
        self.assertContains(response, "Asset QR")
        self.assertContains(response, "Website QR")
        self.assertContains(response, reverse("assets:barcode", args=[self.asset.pk]))
        self.assertContains(response, "kind=scan")

    def test_default_barcode_image_encodes_asset_code(self):
        with patch("apps.assets.barcode_utils.generate_qr_image", wraps=generate_qr_image) as mock_qr:
            response = self.client.get(reverse("assets:barcode", args=[self.asset.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        mock_qr.assert_called()
        self.assertEqual(mock_qr.call_args.args[0], "AT-QRTOGGLE01")

    def test_scan_kind_barcode_image_encodes_scan_url(self):
        with patch("apps.assets.barcode_utils.generate_qr_image", wraps=generate_qr_image) as mock_qr:
            response = self.client.get(
                reverse("assets:barcode", args=[self.asset.pk]),
                {"kind": "scan"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        mock_qr.assert_called()
        payload = mock_qr.call_args.args[0]
        self.assertIn("/scan/register/AT-QRTOGGLE01/", payload)
        self.assertTrue(payload.startswith("http"))

    def test_scan_kind_uses_qr_even_when_asset_barcode_is_code128(self):
        linear = Asset.objects.create(
            product_name="Printer",
            barcode_value="AT-LINEAR01",
            barcode_type=Asset.BarcodeType.CODE128,
        )
        with patch("apps.assets.barcode_utils.generate_qr_image", wraps=generate_qr_image) as mock_qr:
            response = self.client.get(
                reverse("assets:barcode", args=[linear.pk]),
                {"kind": "scan"},
            )
        self.assertEqual(response.status_code, 200)
        mock_qr.assert_called()
        self.assertIn("/scan/register/AT-LINEAR01/", mock_qr.call_args.args[0])
