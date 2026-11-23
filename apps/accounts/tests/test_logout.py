from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class LogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="x", role=User.Role.STAFF)
        self.client.force_login(self.user)

    def test_nav_logout_is_a_post_form(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertContains(response, 'method="post"')
        self.assertContains(response, reverse("accounts:logout"))
        self.assertContains(response, ">Logout</button>")

    def test_get_logout_shows_confirm_instead_of_405(self):
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log out")
        self.assertContains(response, 'method="post"')

    def test_post_logout_signs_out_and_redirects_to_login(self):
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        follow = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(follow, "/login/?next=/")
