// Google Gemini API 클라이언트를 가져옵니다.
import { GoogleGenerativeAI } from '@google/generative-ai';
// .env 파일의 환경 변수를 로드합니다.
import 'dotenv/config';

// Gemini API 클라이언트를 초기화합니다.
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

/**
 * 자막 텍스트를 받아 Gemini를 통해 요약본을 생성하는 함수입니다.
 */
export async function generateSummary(userPrompt) {
  // 사용할 Gemini 모델을 가져옵니다.
  const model = genAI.getGenerativeModel({
    model: 'gemini-2.5-flash-lite', // 기존 코드의 모델명을 환경에 맞춰 유지
  });

  // Gemini API에 전달할 프롬프트를 구성합니다.
  const prompt = `당신은 IT 제품 리뷰 전문가입니다.
주어진 유튜브 영상 자막을 분석하여, 제품의 주요 특징, 장점, 단점을 요약해주세요.
결과는 반드시 Markdown 형식으로 한국어로 응답해야 합니다.

---
자막:
${userPrompt}`;

  // 콘텐츠 생성을 요청합니다.
  const result = await model.generateContent(prompt);
  const response = await result.response;
  return response.text();
}