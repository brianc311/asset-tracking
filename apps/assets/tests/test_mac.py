from django.test import SimpleTestCase

from apps.assets.mac import MAC_ERROR, normalize_mac


class NormalizeMacTests(SimpleTestCase):
    def test_colon_form(self):
        self.assertEqual(normalize_mac("aa:bb:cc:dd:ee:ff"), "AA:BB:CC:DD:EE:FF")

    def test_hyphen_dots_spaces_and_bare_hex(self):
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-ff"), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(normalize_mac("aabb.ccddee.ff"), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(normalize_mac("aa bb cc dd ee ff"), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(normalize_mac("aabbccddeeff"), "AA:BB:CC:DD:EE:FF")

    def test_rejects_invalid(self):
        with self.assertRaisesMessage(ValueError, MAC_ERROR):
            normalize_mac("not-a-mac")
        with self.assertRaisesMessage(ValueError, MAC_ERROR):
            normalize_mac("")

    def test_accepts_letters_beyond_hex(self):
        self.assertEqual(normalize_mac("1A-23-7G-4E-12-9A"), "1A:23:7G:4E:12:9A")

    def test_rejects_symbols(self):
        with self.assertRaisesMessage(ValueError, "Invalid character(s): !"):
            normalize_mac("1A237C4E129!")
