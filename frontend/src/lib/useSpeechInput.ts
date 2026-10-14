"use client";

/**
 * 브라우저 내장 음성인식(Web Speech API)으로 말한 내용을 글자로 받는다.
 * Chrome·Edge·Safari 지원. https 또는 localhost에서만 동작한다 (마이크 권한 정책).
 */
import { useCallback, useEffect, useRef, useState } from "react";

// 표준 타입이 lib.dom에 없어 쓰는 부분만 선언
interface RecognitionResult {
  isFinal: boolean;
  0: { transcript: string };
}
interface RecognitionEvent {
  resultIndex: number;
  results: ArrayLike<RecognitionResult>;
}
interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: RecognitionEvent) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}
type RecognitionCtor = new () => Recognition;

function getCtor(): RecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const ERROR_TEXT: Record<string, string> = {
  "not-allowed": "마이크 권한이 막혀 있어요. 주소창의 마이크 설정에서 허용해 주세요.",
  "service-not-allowed": "이 브라우저에서 음성인식이 허용되지 않았어요.",
  "audio-capture": "마이크를 찾지 못했어요.",
  network: "음성인식 서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.",
};

/**
 * @param onText 말한 내용(확정 + 인식 중) 전체를 넘겨준다. 시작 시점의 입력값 뒤에 이어 붙인다.
 */
export function useSpeechInput(onText: (text: string) => void) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<Recognition | null>(null);
  const baseRef = useRef("");
  const onTextRef = useRef(onText);
  onTextRef.current = onText;

  useEffect(() => {
    // 마이크는 https·localhost에서만 열린다
    setSupported(!!getCtor() && window.isSecureContext);
  }, []);

  const stop = useCallback(() => {
    recRef.current?.stop();
  }, []);

  const start = useCallback((currentText: string) => {
    const Ctor = getCtor();
    if (!Ctor) return;
    setError(null);
    const rec = new Ctor();
    rec.lang = "ko-KR";
    rec.continuous = true;
    rec.interimResults = true;
    baseRef.current = currentText.trim() ? `${currentText.trim()} ` : "";

    // results는 이번 듣기의 누적 목록이라 매번 처음부터 다시 이어 붙인다 (확정된 부분이 두 번 붙지 않게)
    rec.onresult = (e) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      onTextRef.current(baseRef.current + text);
    };
    rec.onerror = (e) => {
      if (e.error !== "no-speech" && e.error !== "aborted") {
        setError(ERROR_TEXT[e.error] ?? `음성인식 오류: ${e.error}`);
      }
    };
    rec.onend = () => {
      setListening(false);
      recRef.current = null;
    };
    recRef.current = rec;
    rec.start();
    setListening(true);
  }, []);

  // 화면을 벗어나면 마이크를 끈다
  useEffect(() => () => recRef.current?.stop(), []);

  return { supported, listening, error, start, stop };
}
