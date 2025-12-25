// express 프레임워크를 가져옵니다.
import express from 'express';
// CORS 미들웨어를 가져옵니다.
import cors from 'cors';
// 작성한 서비스 함수들을 가져옵니다.
import { fetchCaptions } from './services/youtubeService.js';
import { generateSummary } from './services/geminiService.js';

// Express 애플리케이션을 생성합니다.
const server = express();

// CORS를 활성화하여 Frontend에서의 요청을 허용합니다.
server.use(cors({ origin: ['http://localhost:5173', 'http://127.0.0.1:5173'] }));

// 환경 변수에서 포트를 가져오거나 기본값으로 3000을 사용합니다.
const port = process.env.PORT || 3000;

// 루트 경로('/')에 대한 GET 요청을 처리하는 핸들러입니다.
server.get('/', async (req, res) => {
  // 쿼리 파라미터에서 videoId를 가져옵니다.
  const { videoId } = req.query;

  // videoId가 제공되지 않았으면 400 오류를 반환합니다.
  if (!videoId) {
    return res.status(400).json({ error: '요청에 비디오 ID(videoId)를 포함해주세요.' });
  }

  // 1. 자막을 가져옵니다.
  const userPrompt = await fetchCaptions(videoId);

  // 자막을 가져오는 데 실패했거나 자막이 없는 경우 처리
  if (userPrompt === null) {
    return res.status(500).json({ error: '자막을 가져오는 데 실패했습니다.' });
  }
  if (!userPrompt) {
    return res.status(404).json({ error: '해당 영상에 자막이 존재하지 않습니다.' });
  }

  try {
    // 2. 가져온 자막으로 요약을 생성합니다.
    const aiResponseText = await generateSummary(userPrompt);

    // AI 응답 텍스트를 그대로 클라이언트에 전송합니다.
    res.send(aiResponseText);

  } catch (error) {
    // Gemini API 호출 중 오류 발생 시
    console.error("Gemini API 호출 중 오류 발생:", error);
    res.status(500).json({ error: 'AI 처리 중 오류가 발생했습니다.' });
  }
});

// 지정된 포트에서 서버를 시작합니다.
server.listen(port, () => {
  console.log(`${port}번 포트에서 서버 대기 중`);
});