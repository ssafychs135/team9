# Django의 기본 URL 함수를 import합니다.
from django.urls import path
from . import views


# --- 기존 웹 페이지 URL ---
app_name = "reviews"
urlpatterns = [
    # 웹 페이지용 URL들
    path("create/", views.create, name="create"),
    path("<int:review_pk>/", views.detail, name="detail"),
    path("<int:review_pk>/update/", views.update, name="update"),
    path("<int:review_pk>/delete/", views.delete, name="delete"),
    path("", views.index, name="index"),
    path("<int:review_pk>/create_comment", views.create_comment, name="create_comment"),
    path(
        "<int:review_pk>/delete_comment/<int:comment_pk>",
        views.delete_comment,
        name="delete_comment",
    ),
]

