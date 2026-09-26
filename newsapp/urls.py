from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('save/', views.save_article, name='save_article'),
    path('saved/', views.saved_articles, name='saved_articles'),
    path('saved/export/', views.export_saved_articles, name='export_saved_articles'),
    path('delete/', views.delete_article, name='delete_article'),
    path('article/extract/', views.extract_article_content, name='extract_article_content'),
    
    # Profile analytics view route endpoint
    path('profile/', views.profile_analytics, name='profile'),
    path('profile/clear-history/', views.clear_search_history, name='clear_search_history'),
    
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_user, name='logout'),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path(
    "forgot-password/",
    views.forgot_password,
    name="forgot_password"
),

path(
    "verify-otp/",
    views.verify_otp,
    name="verify_otp"
),

path(
    "reset-password/",
    views.reset_password,
    name="reset_password"
),
]