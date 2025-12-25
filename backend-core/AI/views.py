# AI/views.py

import json
import os
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from langchain_core.messages import AIMessage, HumanMessage

from .chatbot_service import get_conversational_rag_chain, initialize_chatbot

# 서버 시작 시 LLM 및 Retriever 초기화
try:
    initialize_chatbot()
    print("챗봇 초기화 완료 (웹 챗봇용).")
except Exception as e:
    print(f"챗봇 초기화 실패: {e}")

def chatbot_page(request):
    """
    챗봇 UI 페이지를 렌더링하고, 세션에 대화 기록이 없으면 초기화합니다.
    """
    if "chat_history" not in request.session:
        request.session['chat_history'] = []
    return render(request, 'AI/chatbot.html')

@csrf_exempt
def chatbot_api(request):
    """
    사용자의 질문을 받아 대화형 챗봇 답변을 반환하는 API 뷰입니다.
    Django 세션을 사용하여 대화 기록을 관리합니다.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('query', '')

            if not user_input:
                return JsonResponse({'error': '질문이 제공되지 않았습니다.'}, status=400)

            # 세션에서 대화 기록 가져오기 (없으면 빈 리스트)
            chat_history_json = request.session.get('chat_history', [])
            
            # JSON 직렬화된 기록을 AIMessage/HumanMessage 객체로 변환
            chat_history = [
                HumanMessage(content=msg['content']) if msg['type'] == 'human' else AIMessage(content=msg['content'])
                for msg in chat_history_json
            ]

            # 대화형 RAG 체인 가져오기
            conversational_rag_chain = get_conversational_rag_chain()
            
            # 체인 실행
            response = conversational_rag_chain.invoke(
                {"input": user_input, "chat_history": chat_history}
            )
            
            # 새로운 질문과 답변을 대화 기록에 추가
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=response["answer"]))

            # AIMessage/HumanMessage 객체를 다시 JSON 직렬화 가능한 형태로 변환하여 세션에 저장
            request.session['chat_history'] = [
                {'type': 'human', 'content': msg.content} if isinstance(msg, HumanMessage) else {'type': 'ai', 'content': msg.content}
                for msg in chat_history
            ]

            return JsonResponse({'response': response["answer"]})

        except json.JSONDecodeError:
            return JsonResponse({'error': '유효하지 않은 JSON 형식입니다.'}, status=400)
        except Exception as e:
            # 실제 운영 환경에서는 더 구체적인 로깅과 에러 처리가 필요합니다.
            print(f"챗봇 처리 중 오류 발생: {e}")
            return JsonResponse({'error': f'챗봇 처리 중 오류 발생: {e}'}, status=500)
    
    return JsonResponse({'error': 'POST 요청만 허용됩니다.'}, status=405)