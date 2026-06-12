from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('save/', views.save_article, name='save_article'),
    path('saved/', views.saved_articles, name='saved_articles'),
    path('delete/', views.delete_article, name='delete_article'),
    
    # Profile analytics view route endpoint
    path('profile/', views.profile_analytics, name='profile'),
    
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_user, name='logout'),
]