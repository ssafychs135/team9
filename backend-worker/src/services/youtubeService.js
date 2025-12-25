// youtube-caption-extractor에서 getSubtitles 함수를 가져옵니다.
import { getSubtitles } from 'youtube-caption-extractor';

/**
 * YouTube 비디오 ID와 언어 코드를 사용하여 자막을 가져오는 비동기 함수입니다.
 */
export async function fetchCaptions(videoId, langCode = 'ko') {
  try {
    // 지정된 비디오 ID와 언어로 자막을 요청합니다.
    const subtitles = await getSubtitles({
      videoID: videoId,
      lang: langCode
    });

    // 자막 배열을 하나의 문자열로 합칩니다.
    const output = subtitles.map(sub => sub.text).join(' ');
    return output;

  } catch (error) {
    // 오류 발생 시 콘솔에 오류를 기록하고 null을 반환합니다.
    console.error('자막 추출 오류:', error);
    return null;
  }
}