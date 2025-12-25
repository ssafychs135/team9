from django.urls import path, include

app_name = 'accounts'
urlpatterns = [
    # dj-rest-auth 경로 추가
    path('signin/', include('dj_rest_auth.urls')),
    path('signup/', include('dj_rest_auth.registration.urls')),
]
