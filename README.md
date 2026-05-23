# 프로젝트 작동 방법
  1. setup_project.py 실행
   - 성공적으로 완료되었다면 .env(backend-core, backend-worker) 의 키 값을 채워야 합니다.
   - `backend-core/.env`: LM Studio 식별자 — `LM_STUDIO_CHAT_MODEL`, `LM_STUDIO_EMBED_MODEL`
   - `backend-worker/.env`: `GEMINI_API_KEY`

  2. LM Studio 게이트웨이 (외부)
   - 별도 서빙 인스턴스가 `https://lmstudio.chs135.com/v1` 에서 동작하며, body 의 `"model"` 필드 기준으로 백엔드에 라우팅합니다.
   - `LM_STUDIO_API_KEY` 는 게이트웨이 Bearer 토큰으로 사용 — 발급받은 키 값을 .env 에 넣어주세요.
   - 챗 모델(예: Gemma 4 E4B Q6), 임베딩 모델(EmbeddingGemma Q8) 둘 다 게이트웨이에서 라우팅됩니다.
   - 임베딩 모델 교체 후에는 ChromaDB 재인덱싱이 필요합니다:
     ```
     cd backend-core && source venv/bin/activate
     python manage.py reset_chroma_collections --purge-all
     python manage.py embed_iphone_data
     ```

  3. run_services.py
   - 백엔드와 프론트엔드 서비스를 시작해줌 (LM Studio 게이트웨이 접근이 가능해야 챗봇/임베딩 호출이 동작합니다)