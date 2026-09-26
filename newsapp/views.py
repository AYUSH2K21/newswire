import json
import logging
import os
import random
import re
from datetime import timedelta
from hashlib import sha256
from html import unescape
from urllib.parse import urlparse
import requests
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .forms import EmailRegistrationForm, EmailLoginForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import URLValidator
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .models import (NewsCache,SavedArticle,SearchLog,PasswordResetOTP,)
logger = logging.getLogger(__name__)

GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
CACHE_TTL = timedelta(minutes=15)

URL_VALIDATOR = URLValidator(schemes=["http", "https"])


CATEGORIES = {
    "general": "🌐 General",
    "world": "🌍 World",
    "nation": "🏛️ Nation",
    "business": "💼 Business",
    "technology": "💻 Technology",
    "entertainment": "🎬 Entertainment",
    "sports": "⚽ Sports",
    "science": "🔬 Science",
    "health": "🩺 Health",
}


COUNTRIES = {
    "world": "🌐 Global",
    "us": "🇺🇸 United States",
    "in": "🇮🇳 India",
    "gb": "🇬🇧 United Kingdom",
    "ca": "🇨🇦 Canada",
    "au": "🇦🇺 Australia",
}


def _format_article(article):
    if not isinstance(article, dict):
        return None

    published_at = article.get("publishedAt")
    time_ago = "Recently"

    if isinstance(published_at, str) and published_at:
        try:
            published = timezone.datetime.fromisoformat(
                published_at.replace("Z", "+00:00")
            )
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
        "source": {
            "name": source.get("name") or "Global Feed"
        },
        "estimated_reading_time": f"{reading_minutes} min read",
        "time_ago": time_ago,
    }


def _cache_key(namespace, value):
    digest = sha256(
        value.casefold().encode("utf-8")
    ).hexdigest()

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
    warning_msg = None

    cached = NewsCache.objects.filter(
        query=cache_key
    ).first()

    if cached and timezone.now() - cached.cached_at < CACHE_TTL:
        return _safe_cached_articles(
            cached.response_data
        ), None

    if not GNEWS_API_KEY:
        logger.warning(
            "GNEWS_API_KEY is not configured"
        )

        warning_msg = (
            "GNews API key is missing. "
            "Displaying cached news feed."
        )

        return (
            _safe_cached_articles(
                cached.response_data
            ) if cached else []
        ), warning_msg

    lock_key = f"news-refresh:{cache_key}"

    if not cache.add(
        lock_key,
        True,
        timeout=30
    ):
        return (
            _safe_cached_articles(
                cached.response_data
            ) if cached else []
        ), None

    try:
        req_params = {
            **params,
            "lang": "en",
            "apikey": GNEWS_API_KEY,
        }

        response = requests.get(
            f"https://gnews.io/api/v4/{endpoint}",
            params=req_params,
            timeout=8,
        )

        response.raise_for_status()

        payload = response.json()

        if (
            not isinstance(payload, dict)
            or not isinstance(
                payload.get("articles", []),
                list
            )
        ):
            raise ValueError(
                "Unexpected GNews response format"
            )

        articles = [
            formatted
            for item in payload.get("articles", [])
            if (
                formatted := _format_article(item)
            )
        ]

        NewsCache.objects.update_or_create(
            query=cache_key,
            defaults={
                "response_data": articles
            },
        )

        return articles, None

    except (
        requests.RequestException,
        TypeError,
        ValueError,
    ) as exc:

        logger.warning(
            "GNews request failed for %s: %s",
            cache_key,
            exc,
        )

        warning_msg = (
            "Live news service unavailable. "
            "Displaying cached news feed."
        )

        return (
            _safe_cached_articles(
                cached.response_data
            ) if cached else []
        ), warning_msg

    finally:
        cache.delete(lock_key)


STREAM_CATEGORIES = [
    "general",
    "technology",
    "world",
    "business",
    "science",
    "entertainment",
    "sports",
    "health",
    "nation",
]


def _get_infinite_stream_page(
    page_num,
    category,
    country,
    search_query
):
    try:
        page_num = max(1, int(page_num))
    except (TypeError, ValueError):
        page_num = 1

    base_idx = (
        STREAM_CATEGORIES.index(category)
        if category in STREAM_CATEGORIES
        else 0
    )

    cat_offset = (page_num - 1) // 2
    sub_page = ((page_num - 1) % 2) + 1

    current_cat_idx = (
        base_idx + cat_offset
    ) % len(STREAM_CATEGORIES)

    current_cat = STREAM_CATEGORIES[
        current_cat_idx
    ]

    params = {"max": 10}

    if country != "world":
        params["country"] = country

    if search_query:
        cache_key = _cache_key(
            "search",
            f"{country}:{search_query}:{page_num}"
        )

        params["q"] = search_query

        articles, warning = _get_news(
            cache_key,
            "search",
            params,
        )

    else:
        cache_key = (
            f"category:{current_cat}:{country}"
        )

        params["category"] = current_cat

        articles, warning = _get_news(
            cache_key,
            "top-headlines",
            params,
        )

    if not articles:
        articles = (
            _cached_news(
                "category:general:world"
            )
            +
            _cached_news(
                "category:technology:world"
            )
        )

    start_i = (sub_page - 1) * 6

    chunk = articles[
        start_i:start_i + 6
    ]

    if not chunk and articles:
        chunk = articles[:6]

    return (
        chunk,
        warning,
        current_cat,
        page_num + 1,
    )


def _cached_news(cache_key):
    cached = NewsCache.objects.filter(
        query=cache_key
    ).first()

    return (
        _safe_cached_articles(
            cached.response_data
        )
        if cached
        else []
    )


def _trim_search_history(user, limit=1000):
    cutoff_ids = list(
        SearchLog.objects.filter(
            user=user
        )
        .order_by(
            "-searched_at",
            "-id"
        )
        .values_list(
            "id",
            flat=True
        )[limit - 1:limit]
    )

    if cutoff_ids:
        SearchLog.objects.filter(
            user=user,
            id__lt=cutoff_ids[0]
        ).delete()


@ensure_csrf_cookie
@login_required(login_url="login")
def home(request):

    search_query = (
        request.GET.get("q", "")
        .strip()[:100]
    )

    category = (
        request.GET.get(
            "category",
            "general"
        ).lower()
    )

    country = (
        request.GET.get(
            "country",
            "world"
        ).lower()
    )

    if category not in CATEGORIES:
        category = "general"

    if country not in COUNTRIES:
        country = "world"

    params = {"max": 10}

    if country != "world":
        params["country"] = country

    if search_query:

        cache_key = _cache_key(
            "search",
            f"{country}:{search_query}"
        )

        params["q"] = search_query

        articles, api_warning = _get_news(
            cache_key,
            "search",
            params,
        )

        if "page" not in request.GET:
            SearchLog.objects.create(
                user=request.user,
                keyword=search_query,
            )

            _trim_search_history(
                request.user
            )

    else:

        cache_key = (
            f"category:{category}:{country}"
        )

        params["category"] = category

        articles, api_warning = _get_news(
            cache_key,
            "top-headlines",
            params,
        )

    if not search_query and category == "general":
        trending_articles = articles[:5]

    else:
        trending_key = (
            f"category:general:{country}"
        )

        trending_articles = (
            _cached_news(
                trending_key
            )[:5]
            or
            _cached_news(
                "category:general:world"
            )[:5]
        )

    history = SearchLog.objects.filter(
        user=request.user
    ).order_by("-searched_at")

    seen = set()
    recent_searches = []

    for keyword in history.values_list(
        "keyword",
        flat=True
    )[:100]:

        normalized = keyword.casefold()

        if normalized not in seen:
            seen.add(normalized)
            recent_searches.append(
                keyword
            )

        if len(recent_searches) == 5:
            break

    page_obj = Paginator(
        articles,
        6
    ).get_page(
        request.GET.get(
            "page",
            1
        )
    )

    if (
        request.headers.get(
            "x-requested-with"
        ) == "XMLHttpRequest"
        or
        request.GET.get("format") == "json"
    ):

        page_req = request.GET.get(
            "page",
            1
        )

        (
            chunk,
            stream_warning,
            cur_cat,
            next_p,
        ) = _get_infinite_stream_page(
            page_req,
            category,
            country,
            search_query,
        )

        return JsonResponse({
            "status": "success",
            "articles": chunk,
            "has_next": True,
            "next_page": next_p,
            "page": (
                int(page_req)
                if str(page_req).isdigit()
                else 1
            ),
            "total_pages": 9999,
            "category_name": CATEGORIES.get(
                cur_cat,
                "🌐 General"
            ),
            "api_warning": (
                stream_warning
                or api_warning
            ),
        })

    top_keyword = (
        history
        .values("keyword")
        .annotate(
            search_count=Count(
                "keyword"
            )
        )
        .order_by(
            "-search_count",
            "keyword"
        )
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
            "country": country,
            "countries": COUNTRIES,
            "api_warning": api_warning,
            "recent_searches": recent_searches,
            "total_saved": SavedArticle.objects.filter(
                user=request.user
            ).count(),
            "total_searches": history.count(),
            "top_keyword": (
                top_keyword["keyword"]
                if top_keyword
                else "N/A"
            ),
        },
    )


@login_required(login_url="login")
def profile_analytics(request):

    searches = SearchLog.objects.filter(
        user=request.user
    )

    return render(
        request,
        "newsapp/profile.html",
        {
            "total_saved": SavedArticle.objects.filter(
                user=request.user
            ).count(),
            "total_searches": searches.count(),
            "top_keywords": (
                searches
                .values("keyword")
                .annotate(
                    search_count=Count(
                        "keyword"
                    )
                )
                .order_by(
                    "-search_count"
                )[:5]
            ),
            "recent_searches_list": (
                searches
                .order_by(
                    "-searched_at"
                )[:10]
            ),
        },
    )


@login_required(login_url="login")
@require_POST
def clear_search_history(request):

    deleted_count, _ = (
        SearchLog.objects.filter(
            user=request.user
        ).delete()
    )

    if (
        request.headers.get(
            "x-requested-with"
        ) == "XMLHttpRequest"
    ):
        return JsonResponse({
            "status": "success",
            "deleted": deleted_count,
        })

    return redirect("profile")


@login_required(login_url="login")
def export_saved_articles(request):

    saved_list = (
        SavedArticle.objects.filter(
            user=request.user
        )
        .order_by("-created_at")
    )

    data = [
        {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "image": article.image,
            "created_at": (
                article.created_at.isoformat()
            ),
        }
        for article in saved_list
    ]

    response = HttpResponse(
        json.dumps(
            data,
            indent=2
        ),
        content_type="application/json",
    )

    response["Content-Disposition"] = (
        f'attachment; '
        f'filename="saved_bookmarks_'
        f'{request.user.username}.json"'
    )

    return response


def _extract_full_article(url):

    try:
        URL_VALIDATOR(url)

    except ValidationError:
        return None

    cache_key = _cache_key(
        "extracted",
        url
    )

    cached = NewsCache.objects.filter(
        query=cache_key
    ).first()

    if (
        cached
        and
        timezone.now() - cached.cached_at
        < timedelta(hours=24)
    ):
        return cached.response_data

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0.0.0 "
            "Safari/537.36"
        )
    }

    try:

        res = requests.get(
            url,
            headers=headers,
            timeout=6,
        )

        res.raise_for_status()

        html_content = res.text

    except requests.RequestException as exc:

        logger.warning(
            "Could not fetch article HTML for %s: %s",
            url,
            exc,
        )

        return None

    title_match = re.search(
        r'<meta\s+property=["\']og:title["\']'
        r'\s+content=["\']([^"\']+)["\']',
        html_content,
        re.I,
    )

    if not title_match:

        title_match = re.search(
            r"<title>(.*?)</title>",
            html_content,
            re.I | re.S,
        )

    title = (
        unescape(
            title_match.group(1)
        ).strip()
        if title_match
        else "Extracted Article"
    )

    img_match = re.search(
        r'<meta\s+property=["\']og:image["\']'
        r'\s+content=["\']([^"\']+)["\']',
        html_content,
        re.I,
    )

    lead_image = (
        img_match.group(1).strip()
        if img_match
        else ""
    )

    if lead_image:
        try:
            URL_VALIDATOR(
                lead_image
            )
        except ValidationError:
            lead_image = ""

    parsed_domain = (
        urlparse(url)
        .netloc
        .replace("www.", "")
    )

    raw_p_tags = re.findall(
        r"<p[^>]*>(.*?)</p>",
        html_content,
        re.I | re.S,
    )

    paragraphs = []

    for p in raw_p_tags:

        clean_p = re.sub(
            r"<[^>]+>",
            "",
            p
        ).strip()

        clean_p = unescape(
            clean_p
        )

        if (
            len(clean_p) > 40
            and
            not any(
                k in clean_p.lower()
                for k in [
                    "cookie",
                    "terms of use",
                    "privacy policy",
                    "subscribe now",
                    "all rights reserved",
                ]
            )
        ):

            if clean_p not in paragraphs:
                paragraphs.append(
                    clean_p
                )

    if not paragraphs:

        desc_match = re.search(
            r'<meta\s+name=["\']description["\']'
            r'\s+content=["\']([^"\']+)["\']',
            html_content,
            re.I,
        )

        if desc_match:
            paragraphs.append(
                unescape(
                    desc_match.group(1)
                ).strip()
            )

    total_words = sum(
        len(p.split())
        for p in paragraphs
    )

    reading_time = max(
        1,
        round(
            total_words / 200
        )
    )

    extracted_data = {
        "title": title,
        "lead_image": lead_image,
        "domain": parsed_domain,
        "paragraphs": paragraphs,
        "word_count": total_words,
        "reading_time": (
            f"{reading_time} min read"
        ),
        "url": url,
    }

    NewsCache.objects.update_or_create(
        query=cache_key,
        defaults={
            "response_data": extracted_data
        },
    )

    return extracted_data


@login_required(login_url="login")
def extract_article_content(request):

    target_url = (
        request.GET.get(
            "url",
            ""
        ).strip()
    )

    if not target_url:

        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "URL parameter is required"
                ),
            },
            status=400,
        )

    try:
        URL_VALIDATOR(
            target_url
        )

    except ValidationError:

        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "Invalid HTTP(S) URL"
                ),
            },
            status=400,
        )

    article_data = (
        _extract_full_article(
            target_url
        )
    )

    if (
        not article_data
        or
        not article_data.get(
            "paragraphs"
        )
    ):

        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "Full text extraction "
                    "unavailable for this source"
                ),
            },
            status=404,
        )

    return JsonResponse({
        "status": "success",
        "article": article_data,
    })


@login_required(login_url="login")
@require_POST
def save_article(request):

    title = (
        request.POST.get(
            "title",
            ""
        ).strip()[:300]
    )

    url = (
        request.POST.get(
            "url",
            ""
        ).strip()[:500]
    )

    image = (
        request.POST.get(
            "image",
            ""
        ).strip()[:500]
    )

    if not title or not url:

        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "Title and URL are required"
                ),
            },
            status=400,
        )

    try:

        URL_VALIDATOR(url)

        if image:
            URL_VALIDATOR(image)

    except ValidationError:

        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "Only valid HTTP(S) URLs "
                    "are allowed"
                ),
            },
            status=400,
        )

    _, created = (
        SavedArticle.objects.get_or_create(
            user=request.user,
            url=url,
            defaults={
                "title": title,
                "image": image,
            },
        )
    )

    return JsonResponse({
        "status": (
            "saved"
            if created
            else "exists"
        )
    })


@login_required(login_url="login")
def saved_articles(request):

    saved_news = Paginator(
        SavedArticle.objects.filter(
            user=request.user
        ).order_by(
            "-created_at"
        ),
        12,
    ).get_page(
        request.GET.get(
            "page",
            1
        )
    )

    return render(
        request,
        "newsapp/saved.html",
        {
            "saved_news": saved_news
        },
    )


@login_required(login_url="login")
@require_POST
def delete_article(request):

    try:

        article_id = int(
            request.POST.get(
                "article_id",
                ""
            )
        )

    except (TypeError, ValueError):

        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "Invalid article ID"
                ),
            },
            status=400,
        )

    deleted, _ = (
        SavedArticle.objects.filter(
            id=article_id,
            user=request.user,
        ).delete()
    )

    return JsonResponse(
        {
            "status": (
                "deleted"
                if deleted
                else "error"
            )
        },
        status=(
            200
            if deleted
            else 404
        ),
    )


@ensure_csrf_cookie
def register_user(request):

    if request.user.is_authenticated:
        return redirect("home")

    form = EmailRegistrationForm(
        request.POST or None
    )

    if (
        request.method == "POST"
        and
        form.is_valid()
    ):

        user = form.save()

        login(
            request,
            user
        )

        return redirect("home")

    return render(
        request,
        "newsapp/register.html",
        {
            "form": form
        },
    )


@ensure_csrf_cookie
def login_user(request):

    if request.user.is_authenticated:
        return redirect("home")

    form = EmailLoginForm(
        request.POST or None
    )

    if (
        request.method == "POST"
        and
        form.is_valid()
    ):

        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]

        user = (
            User.objects.filter(
                email__iexact=email
            ).first()
        )

        if user is None or not user.check_password(password):

            form.add_error(
                None,
                "Invalid email or password."
            )

        else:

            login(
                request,
                user
            )

            return redirect("home")

    return render(
        request,
        "newsapp/login.html",
        {
            "form": form
        },
    )


@login_required(login_url="login")
@require_POST
def logout_user(request):

    logout(request)

    return redirect("login")


# =========================================================
# PASSWORD RESET / EMAIL OTP
# =========================================================


def generate_otp():
    """
    Generate a random 6-digit OTP.
    """
    return str(
        random.SystemRandom().randint(
            100000,
            999999
        )
    )


def send_password_reset_otp(user):

    otp = generate_otp()

    # Invalidate all previous unused OTPs
    PasswordResetOTP.objects.filter(
        user=user,
        is_verified=False,
    ).update(
        is_verified=True
    )

    # Create new OTP
    PasswordResetOTP.objects.create(
        user=user,
        otp=otp,
    )

    # Brevo transactional email API
    brevo_api_key = os.getenv("BREVO_API_KEY")
    brevo_sender_email = os.getenv("BREVO_SENDER_EMAIL")
    brevo_sender_name = os.getenv(
        "BREVO_SENDER_NAME",
        "NewsWire",
    )

    if not brevo_api_key:
        logger.error(
            "BREVO_API_KEY is not configured."
        )
        raise RuntimeError(
            "BREVO_API_KEY must be configured "
            "to send password reset emails."
        )

    if not brevo_sender_email:
        logger.error(
            "BREVO_SENDER_EMAIL is not configured."
        )
        raise RuntimeError(
            "BREVO_SENDER_EMAIL must be configured "
            "to send password reset emails."
        )

    email_payload = {
        "sender": {
            "name": brevo_sender_name,
            "email": brevo_sender_email,
        },
        "to": [
            {
                "email": user.email,
            }
        ],
        "subject": "NewsWire Password Reset OTP",
        "textContent": (
            f"Your NewsWire password reset OTP is: {otp}\n\n"
            "This OTP is valid for 5 minutes.\n\n"
            "If you did not request a password reset, "
            "please ignore this email."
        ),
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": brevo_api_key,
                "content-type": "application/json",
            },
            json=email_payload,
            timeout=10,
        )

        response.raise_for_status()

        logger.info(
            "Password reset OTP email sent to %s",
            user.email,
        )

    except requests.RequestException as exc:
        logger.exception(
            "Brevo failed to send password reset OTP "
            "to %s: %s",
            user.email,
            exc,
        )
        raise RuntimeError(
            "Unable to send the password reset email."
        ) from exc


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            return render(
                request,
                "newsapp/forgot_password.html",
                {
                    "error": "Please enter your email address."
                }
            )

        user = User.objects.filter(
            email__iexact=email
        ).first()

        if user:
            send_password_reset_otp(user)

            request.session["password_reset_email"] = email

            # Directly go to OTP screen
            return redirect("verify_otp")

        # Don't reveal whether account exists
        return render(
            request,
            "newsapp/forgot_password.html",
            {
                "success": (
                    "If an account exists with this email, "
                    "an OTP has been sent."
                )
            }
        )

    return render(
        request,
        "newsapp/forgot_password.html"
    )
def verify_otp(request):

    email = request.session.get(
        "password_reset_email"
    )

    if not email:
        return redirect("forgot_password")

    user = User.objects.filter(
        email__iexact=email
    ).first()

    if not user:
        request.session.pop(
            "password_reset_email",
            None
        )
        return redirect("forgot_password")

    if request.method == "POST":

        entered_otp = request.POST.get(
            "otp",
            ""
        ).strip()

        if not entered_otp:

            return render(
                request,
                "newsapp/verify_otp.html",
                {
                    "error": "Please enter the OTP."
                }
            )

        otp_record = (
            PasswordResetOTP.objects
            .filter(
                user=user,
                otp=entered_otp,
                is_verified=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp_record:

            return render(
                request,
                "newsapp/verify_otp.html",
                {
                    "error": "Invalid OTP. Please try again."
                }
            )

        otp_record.is_verified = True

        otp_record.save(
            update_fields=[
                "is_verified"
            ]
        )

        request.session[
            "password_reset_verified"
        ] = True

        return redirect(
            "reset_password"
        )

    return render(
        request,
        "newsapp/verify_otp.html"
    )


def reset_password(request):

    email = request.session.get(
        "password_reset_email"
    )

    verified = request.session.get(
        "password_reset_verified"
    )

    if not email or not verified:
        return redirect(
            "forgot_password"
        )

    user = User.objects.filter(
        email__iexact=email
    ).first()

    if not user:
        request.session.flush()

        return redirect(
            "forgot_password"
        )

    if request.method == "POST":

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        if not password or not confirm_password:

            return render(
                request,
                "newsapp/reset_password.html",
                {
                    "error": (
                        "Please fill in both "
                        "password fields."
                    )
                }
            )

        if password != confirm_password:

            return render(
                request,
                "newsapp/reset_password.html",
                {
                    "error": (
                        "Passwords do not match."
                    )
                }
            )

        if len(password) < 8:

            return render(
                request,
                "newsapp/reset_password.html",
                {
                    "error": (
                        "Password must be at least "
                        "8 characters."
                    )
                }
            )

        # Change password
        user.set_password(password)
        user.save()

        # Clear reset session
        request.session.pop(
            "password_reset_email",
            None
        )

        request.session.pop(
            "password_reset_verified",
            None
        )

        # Show success screen
        return render(
            request,
            "newsapp/password_reset_success.html"
        )

    return render(
        request,
        "newsapp/reset_password.html"
    )