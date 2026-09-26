from django.db import models
from django.contrib.auth.models import User

class SavedArticle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_articles")
    title = models.CharField(max_length=300)
    url = models.URLField(max_length=500)  
    image = models.URLField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-created_at"], name="saved_user_created_idx")]
        constraints = [
            models.UniqueConstraint(fields=["user", "url"], name="unique_user_saved_url")
        ]

    def __str__(self):
        return f"{self.user.username} | {self.title[:50]}"


class NewsCache(models.Model):
    query = models.CharField(max_length=100, unique=True)
    response_data = models.JSONField()  
    cached_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cache for query: {self.query}"


# User search history logging
class SearchLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="search_logs")
    keyword = models.CharField(max_length=100)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-searched_at"], name="search_user_time_idx")]

    def __str__(self):
        return f"{self.user.username} searched for '{self.keyword}' at {self.searched_at.strftime('%Y-%m-%d %H:%M')}"

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_otps"
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Password reset OTP - {self.user.username}"
