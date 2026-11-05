from unittest.mock import patch

from django.test import SimpleTestCase

from apps.assets.barcode_utils import barcode_data_uri


class BarcodeDataUriTests(SimpleTestCase):
    def test_returns_empty_string_when_barcode_generation_fails(self):
        with patch(
            "apps.assets.barcode_utils.barcode_png_for_value",
            side_effect=ValueError("invalid barcode"),
        ):
            self.assertEqual(barcode_data_uri("bad\x00value"), "")
