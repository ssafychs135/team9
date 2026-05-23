# AI/views.py

import json
import os
import sys
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from langchain_core.messages import AIMessage, HumanMessage

from .chatbot_service import initialize_chatbot
from .graph import get_chatbot_graph

# 서버 시작 시 LLM 및 Retriever 초기화
try:
    initialize_chatbot()
    sys.stderr.write("챗봇 초기화 완료 (웹 챗봇용).\n")
except Exception as e:
    sys.stderr.write(f"챗봇 초기화 실패: {e}\n")

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

            # LangGraph chatbot graph 가져오기
            graph = get_chatbot_graph()

            # 그래프 실행 — 최종 state dict 반환
            result = graph.invoke(
                {"input": user_input, "chat_history": chat_history}
            )

            answer_text = result.get("answer", "")

            # 새로운 질문과 답변을 대화 기록에 추가
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=answer_text))

            # AIMessage/HumanMessage 객체를 다시 JSON 직렬화 가능한 형태로 변환하여 세션에 저장
            request.session['chat_history'] = [
                {'type': 'human', 'content': msg.content} if isinstance(msg, HumanMessage) else {'type': 'ai', 'content': msg.content}
                for msg in chat_history
            ]

            return JsonResponse({'response': answer_text})

        except json.JSONDecodeError:
            return JsonResponse({'error': '유효하지 않은 JSON 형식입니다.'}, status=400)
        except Exception as e:
            # 실제 운영 환경에서는 더 구체적인 로깅과 에러 처리가 필요합니다.
            sys.stderr.write(f"챗봇 처리 중 오류 발생: {e}\n")
            return JsonResponse({'error': f'챗봇 처리 중 오류 발생: {e}'}, status=500)

    return JsonResponse({'error': 'POST 요청만 허용됩니다.'}, status=405)


def _history_to_messages(history_json):
    """세션 JSON 형태 → LangChain Message 객체 리스트."""
    return [
        HumanMessage(content=m['content']) if m['type'] == 'human' else AIMessage(content=m['content'])
        for m in history_json
    ]


def _messages_to_history(messages):
    """LangChain Message 객체 리스트 → 세션 JSON 형태."""
    return [
        {'type': 'human', 'content': m.content} if isinstance(m, HumanMessage) else {'type': 'ai', 'content': m.content}
        for m in messages
    ]


@csrf_exempt
@require_POST
def chatbot_stream_api(request):
    """SSE 스트리밍 + 멀티턴 챗봇 API.

    응답 형식: ``data: {"chunk": "..."}\\n\\n`` 반복 → ``data: [DONE]\\n\\n``.
    Django session cookie 로 chat_history 누적 (멀티턴).
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '유효하지 않은 JSON 형식입니다.'}, status=400)

    user_input = (data.get('query') or '').strip()
    if not user_input:
        return JsonResponse({'error': '질문이 제공되지 않았습니다.'}, status=400)

    chat_history_json = request.session.get('chat_history', [])
    chat_history = _history_to_messages(chat_history_json)

    # StreamingHttpResponse 는 generator 안에서 session 수정해도 그 시점엔 이미
    # response header 가 클라이언트로 떠난 뒤라 Set-Cookie 가 전송 안 됨.
    # 첫 chunk 보내기 전에 session 을 명시 save 해서 sessionid cookie 가
    # response header 작성 시점에 박히도록 보장 (멀티턴 동작의 전제 조건).
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
    request.session.save()

    graph = get_chatbot_graph()

    # 사용자에게 token 을 그대로 보여줘야 하는 노드 = LLM 답변을 생성하는 노드.
    # router/contextualize/extract_models 의 chunk 는 내부 reasoning 이라 filter.
    _USER_FACING_NODES = {"compose_answer", "general_chat"}

    def event_stream():
        full_answer_parts: list[str] = []
        try:
            # stream_mode="messages" : 매 LLM token chunk 마다 (chunk, metadata) emit.
            # metadata["langgraph_node"] 로 어느 노드의 chunk 인지 식별.
            for chunk, metadata in graph.stream(
                {"input": user_input, "chat_history": chat_history},
                stream_mode="messages",
            ):
                node = metadata.get("langgraph_node", "") if metadata else ""
                if node not in _USER_FACING_NODES:
                    continue
                piece = getattr(chunk, "content", "") or ""
                if not piece:
                    continue
                full_answer_parts.append(piece)
                yield f"data: {json.dumps({'chunk': piece}, ensure_ascii=False)}\n\n"
        except Exception as e:
            sys.stderr.write(f"챗봇 스트리밍 중 오류: {e}\n")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            return

        # 스트림 종료 후 session 에 한 턴 누적.
        # StreamingHttpResponse 는 SessionMiddleware 의 자동 save 가 stream 시작 전에
        # 이미 끝나므로, generator 안의 session 수정은 명시 save() 없이는 휘발.
        # 따라서 직접 save() 를 호출해야 다음 요청에 history 가 보존됨.
        full_answer = "".join(full_answer_parts)
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=full_answer))
        request.session['chat_history'] = _messages_to_history(chat_history)
        request.session.save()
        yield "data: [DONE]\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    # Nginx 등 reverse proxy 의 buffering 차단 (도커/배포 시 필수)
    response['X-Accel-Buffering'] = 'no'
    return response


@csrf_exempt
@require_POST
def chatbot_reset_api(request):
    """세션의 chat_history 초기화 ('새 대화' UX 용)."""
    request.session['chat_history'] = []
    request.session.modified = True
    return JsonResponse({'ok': True})