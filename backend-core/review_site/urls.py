"""
URL configuration for review_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from dj_rest_auth.registration.views import VerifyEmailView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("reviews/", include("reviews.urls")), # reviews 앱의 웹 페이지 URL
    path("ai/", include("AI.urls")),
    path("api/reviews/", include("reviews.api_urls")), # reviews 앱의 API URL
    
    # 브라우저에서 로그인/로그아웃 테스트를 하기 위한 URL
    path('api-auth/', include('rest_framework.urls')),

    # 이메일 인증 URL (allauth가 네임스페이스 없이 찾을 수 있도록 여기에 정의)
    re_path(r'^account-confirm-email/(?P<key>[-:\w]+)/$', VerifyEmailView.as_view(), name='account_confirm_email'),
]
