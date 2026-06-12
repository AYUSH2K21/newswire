import logging
import os
from hashlib import sha256
from datetime import timedelta

import requests
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import NewsCache, SavedArticle, SearchLog

logger = logging.getLogger(__name__)

GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
CACHE_TTL = timedelta(minutes=15)
URL_VALIDATOR = URLValidator(schemes=["http", "https"])
CATEGORIES = {
    "general": "General",
    "world": "World",
    "nation": "Nation",
    "business": "Business",
    "technology": "Technology",
    "entertainment": "Entertainment",
    "sports": "Sports",
    "science": "Science",
    "health": "Health",
}


def _format_article(article):
    if not isinstance(article, dict):
        return None
    published_at = article.get("publishedAt")
    time_ago = "Recently"
    if isinstance(published_at, str) and published_at:
        try:
            published = timezone.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            elapsed = max(timezone.now() - published, timedelta())
            if elapsed.days:
                time_ago = f"{elapsed.days}d ago"
            elif elapsed.seconds >= 3600:
                time_ago = f"{elapsed.seconds // 3600}h ago"
            else:
                time_ago = f"{max(1, elapsed.seconds // 60)}m ago"
        except (TypeError, ValueError):
            pass

    title = article.get("title") or "Untitled article"
    description = article.get("description") or ""
    if not isinstance(title, str):
        title = "Untitled article"
    if not isinstance(description, str):
        description = ""
    url = article.get("url") or ""
    image = article.get("image") or ""
    try:
        URL_VALIDATOR(url)
    except ValidationError:
        return None
    if image:
        try:
            URL_VALIDATOR(image)
        except ValidationError:
            image = ""
    word_count = len(title.split()) + len(description.split())
    reading_minutes = max(1, round(word_count / 200))
    source = article.get("source")
    if not isinstance(source, dict):
        source = {}
    return {
        "title": title,
        "description": description,
        "url": url,
        "urlToImage": image,
        "source": {"name": source.get("name") or "Global Feed"},
        "estimated_reading_time": f"{reading_minutes} min read",
        "time_ago": time_ago,
    }


def _cache_key(namespace, value):
    digest = sha256(value.casefold().encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def _safe_cached_articles(items):
    safe_articles = []
    if not isinstance(items, list):
        return safe_articles
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or ""
        try:
            URL_VALIDATOR(url)
        except ValidationError:
            continue
        article = item.copy()
        image = article.get("urlToImage") or ""
        if image:
            try:
                URL_VALIDATOR(image)
            except ValidationError:
                article["urlToImage"] = ""
        safe_articles.append(article)
    return safe_articles


def _get_news(cache_key, endpoint, params):
    cached = NewsCache.objects.filter(query=cache_key).first()
    if cached and timezone.now() - cached.cached_at < CACHE_TTL:
        return _safe_cached_articles(cached.response_data)

    if not GNEWS_API_KEY:
        logger.warning("GNEWS_API_KEY is not configured")
        return _safe_cached_articles(cached.response_data) if cached else []

    lock_key = f"news-refresh:{cache_key}"
    if not cache.add(lock_key, True, timeout=30):
        return _safe_cached_articles(cached.response_data) if cached else []

    try:
        response = requests.get(
            f"https://gnews.io/api/v4/{endpoint}",
            params={**params, "lang": "en", "apikey": GNEWS_API_KEY},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("articles", []), list):
            raise ValueError("Unexpected GNews response format")
        articles = [formatted for item in payload.get("articles", []) if (formatted := _format_article(item))]
        NewsCache.objects.update_or_create(
            query=cache_key,
            defaults={"response_data": articles},
        )
        return articles
    except (requests.RequestException, TypeError, ValueError) as exc:
        logger.warning("GNews request failed for %s: %s", cache_key, exc)
        return _safe_cached_articles(cached.response_data) if cached else []
    finally:
        cache.delete(lock_key)


def _cached_news(cache_key):
    cached = NewsCache.objects.filter(query=cache_key).first()
    return _safe_cached_articles(cached.response_data) if cached else []


def _trim_search_history(user, limit=1000):
    cutoff_ids = list(
        SearchLog.objects.filter(user=user)
        .order_by("-searched_at", "-id")
        .values_list("id", flat=True)[limit - 1:limit]
    )
    if cutoff_ids:
        SearchLog.objects.filter(user=user, id__lt=cutoff_ids[0]).delete()


@login_required(login_url="login")
def home(request):
    search_query = request.GET.get("q", "").strip()[:100]
    category = request.GET.get("category", "general").lower()
    if category not in CATEGORIES:
        category = "general"

    if search_query:
        cache_key = _cache_key("search", search_query)
        articles = _get_news(cache_key, "search", {"q": search_query, "max": 10})
        if "page" not in request.GET:
            SearchLog.objects.create(user=request.user, keyword=search_query)
            _trim_search_history(request.user)
    else:
        cache_key = f"category:{category}"
        articles = _get_news(
            cache_key,
            "top-headlines",
            {"category": category, "country": "in", "max": 10},
        )

    if not search_query and category == "general":
        trending_articles = articles[:5]
    else:
        trending_articles = _cached_news("category:general")[:5]

    history = SearchLog.objects.filter(user=request.user).order_by("-searched_at")
    seen = set()
    recent_searches = []
    for keyword in history.values_list("keyword", flat=True)[:100]:
        normalized = keyword.casefold()
        if normalized not in seen:
            seen.add(normalized)
            recent_searches.append(keyword)
        if len(recent_searches) == 5:
            break

    page_obj = Paginator(articles, 9).get_page(request.GET.get("page", 1))
    top_keyword = (
        history.values("keyword")
        .annotate(search_count=Count("keyword"))
        .order_by("-search_count", "keyword")
        .first()
    )
    return render(
        request,
        "newsapp/home.html",
        {
            "articles": page_obj,
            "trending_articles": trending_articles,
            "q": search_query,
            "category": category,
            "categories": CATEGORIES,
            "recent_searches": recent_searches,
            "total_saved": SavedArticle.objects.filter(user=request.user).count(),
            "total_searches": history.count(),
            "top_keyword": top_keyword["keyword"] if top_keyword else "N/A",
        },
    )


@login_required(login_url="login")
def profile_analytics(request):
    searches = SearchLog.objects.filter(user=request.user)
    return render(request, "newsapp/profile.html", {
        "total_saved": SavedArticle.objects.filter(user=request.user).count(),
        "total_searches": searches.count(),
        "top_keywords": searches.values("keyword").annotate(
            search_count=Count("keyword")
        ).order_by("-search_count")[:3],
    })


@login_required(login_url="login")
@require_POST
def save_article(request):
    title = request.POST.get("title", "").strip()[:300]
    url = request.POST.get("url", "").strip()[:500]
    image = request.POST.get("image", "").strip()[:500]
    if not title or not url:
        return JsonResponse({"status": "error", "message": "Title and URL are required"}, status=400)
    try:
        URL_VALIDATOR(url)
        if image:
            URL_VALIDATOR(image)
    except ValidationError:
        return JsonResponse({"status": "error", "message": "Only valid HTTP(S) URLs are allowed"}, status=400)

    _, created = SavedArticle.objects.get_or_create(
        user=request.user,
        url=url,
        defaults={"title": title, "image": image},
    )
    return JsonResponse({"status": "saved" if created else "exists"})


@login_required(login_url="login")
def saved_articles(request):
    saved_news = Paginator(
        SavedArticle.objects.filter(user=request.user).order_by("-created_at"), 12
    ).get_page(request.GET.get("page", 1))
    return render(request, "newsapp/saved.html", {"saved_news": saved_news})


@login_required(login_url="login")
@require_POST
def delete_article(request):
    try:
        article_id = int(request.POST.get("article_id", ""))
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Invalid article ID"}, status=400)
    deleted, _ = SavedArticle.objects.filter(
        id=article_id, user=request.user
    ).delete()
    return JsonResponse({"status": "deleted" if deleted else "error"}, status=200 if deleted else 404)


def register_user(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")
    return render(request, "newsapp/register.html", {"form": form})


def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("home")
    return render(request, "newsapp/login.html", {"form": form})


@login_required(login_url="login")
@require_POST
def logout_user(request):
    logout(request)
    return redirect("login")
