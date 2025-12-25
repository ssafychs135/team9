# reviews/api_urls.py
from django.urls import path, include
from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter
from . import views

# --- API URL 설정을 위한 Router ---
router = DefaultRouter()
# 최상위 URL 설정 파일에서 'api/reviews/' 접두사가 이미 붙었으므로, 여기서는 빈 문자열로 등록합니다.
router.register(r"", views.ReviewViewSet, basename="reviews-api")

# ReviewViewSet에 중첩된 CommentViewSet을 위한 라우터를 생성합니다.
# 상위 라우터의 접두사가 빈 문자열이므로 parent_prefix도 빈 문자열로 설정합니다.
comments_router = NestedDefaultRouter(router, r"", lookup="review")
comments_router.register("comments", views.CommentViewSet, basename="review-comments")

# 이 파일의 urlpatterns는 router와 comments_router에 의해 생성된
# 모든 API URL들을 포함하게 됩니다.
urlpatterns = [
    path("", include(router.urls)),
    path("", include(comments_router.urls)),
]
