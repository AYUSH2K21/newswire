from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import SavedArticle, SearchLog
from .views import _format_article


class NewsAppTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def login(self):
        self.client.force_login(self.user)

    def test_home_page_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)

    @patch("newsapp.views._get_news", return_value=[])
    def test_search_is_logged_once_when_paginating(self, _get_news):
        self.login()
        self.client.get(reverse("home"), {"q": "security"})
        self.client.get(reverse("home"), {"q": "security", "page": 2})
        self.assertEqual(SearchLog.objects.count(), 1)

    @patch("newsapp.views._get_news", return_value=[])
    def test_long_search_does_not_overflow_cache_key(self, _get_news):
        self.login()
        response = self.client.get(reverse("home"), {"q": "x" * 100})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(_get_news.call_args_list[0].args[0]), 100)

    def test_save_article_and_prevent_duplicate(self):
        self.login()
        data = {"title": "Test News", "url": "https://example.com/news", "image": ""}
        first = self.client.post(reverse("save_article"), data)
        second = self.client.post(reverse("save_article"), data)
        self.assertEqual(first.json()["status"], "saved")
        self.assertEqual(second.json()["status"], "exists")
        self.assertEqual(SavedArticle.objects.count(), 1)

    def test_save_article_rejects_unsafe_url(self):
        self.login()
        response = self.client.post(reverse("save_article"), {
            "title": "Unsafe", "url": "javascript:alert(1)", "image": ""
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SavedArticle.objects.count(), 0)

    def test_malformed_api_article_is_handled(self):
        article = _format_article({
            "title": ["invalid"],
            "description": {"invalid": True},
            "publishedAt": ["invalid"],
            "url": "https://example.com/article",
            "source": "invalid",
        })
        self.assertEqual(article["title"], "Untitled article")
        self.assertEqual(article["description"], "")

    def test_delete_rejects_malformed_id(self):
        self.login()
        response = self.client.post(reverse("delete_article"), {"article_id": "bad"})
        self.assertEqual(response.status_code, 400)

    def test_user_cannot_delete_another_users_bookmark(self):
        other = User.objects.create_user(username="other", password="pass12345")
        article = SavedArticle.objects.create(
            user=other, title="Other", url="https://example.com/other"
        )
        self.login()
        response = self.client.post(reverse("delete_article"), {"article_id": article.id})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SavedArticle.objects.filter(id=article.id).exists())

    def test_logout_requires_post(self):
        self.login()
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)

    def test_saved_articles_are_paginated(self):
        self.login()
        SavedArticle.objects.bulk_create([
            SavedArticle(user=self.user, title=f"Article {number}", url=f"https://example.com/{number}")
            for number in range(13)
        ])
        response = self.client.get(reverse("saved_articles"))
        self.assertEqual(len(response.context["saved_news"]), 12)

    def test_profile_page_access(self):
        self.login()
        self.assertEqual(self.client.get(reverse("profile")).status_code, 200)

    def test_authenticated_user_redirected_from_auth_pages(self):
        self.login()
        self.assertRedirects(self.client.get(reverse("login")), reverse("home"))
        self.assertRedirects(self.client.get(reverse("register")), reverse("home"))
