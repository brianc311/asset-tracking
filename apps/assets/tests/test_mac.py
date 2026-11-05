from django.test import SimpleTestCase

from apps.assets.mac import MAC_ERROR, normalize_mac


class NormalizeMacTests(SimpleTestCase):
    def test_colon_form(self):
        self.assertEqual(normalize_mac("aa:bb:cc:dd:ee:ff"), "AA:BB:CC:DD:EE:FF")

    def test_hyphen_and_bare_hex(self):
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-ff"), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(normalize_mac("aabbccddeeff"), "AA:BB:CC:DD:EE:FF")

    def test_rejects_invalid(self):
        with self.assertRaisesMessage(ValueError, MAC_ERROR):
            normalize_mac("not-a-mac")
        with self.assertRaisesMessage(ValueError, MAC_ERROR):
            normalize_mac("")
