from django.contrib import admin
from django.urls import path, include

from newsapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('newsapp.urls')),
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