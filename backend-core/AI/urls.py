# AI/urls.py

from django.urls import path
from . import views

app_name = 'AI' # 앱 이름 공간 설정 (선택 사항이지만 권장)

urlpatterns = [
    path('chatbot/', views.chatbot_page, name='chatbot_page'), # 챗봇 UI 페이지
    path('chatbot/api/', views.chatbot_api, name='chatbot_api'), # 챗봇 API 엔드포인트 (단발)
    path('chatbot/stream/', views.chatbot_stream_api, name='chatbot_stream_api'), # SSE 스트리밍
    path('chatbot/reset/', views.chatbot_reset_api, name='chatbot_reset_api'), # 멀티턴 세션 초기화
]
