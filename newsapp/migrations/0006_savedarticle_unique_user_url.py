from django.db import migrations, models
from urllib.parse import urlsplit


def clean_bookmarks(apps, schema_editor):
    SavedArticle = apps.get_model("newsapp", "SavedArticle")
    seen = set()
    duplicate_ids = []
    for article in SavedArticle.objects.order_by("id").iterator():
        parsed_url = urlsplit(article.url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            duplicate_ids.append(article.id)
            continue
        if article.image:
            parsed_image = urlsplit(article.image)
            if parsed_image.scheme not in {"http", "https"} or not parsed_image.netloc:
                article.image = ""
                article.save(update_fields=["image"])
        key = (article.user_id, article.url)
        if key in seen:
            duplicate_ids.append(article.id)
        else:
            seen.add(key)
    if duplicate_ids:
        SavedArticle.objects.filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):
    dependencies = [("newsapp", "0005_searchlog")]

    operations = [
        migrations.RunPython(clean_bookmarks, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="savedarticle",
            constraint=models.UniqueConstraint(
                fields=("user", "url"), name="unique_user_saved_url"
            ),
        ),
        migrations.AddIndex(
            model_name="savedarticle",
            index=models.Index(fields=["user", "-created_at"], name="saved_user_created_idx"),
        ),
        migrations.AddIndex(
            model_name="searchlog",
            index=models.Index(fields=["user", "-searched_at"], name="search_user_time_idx"),
        ),
    ]
