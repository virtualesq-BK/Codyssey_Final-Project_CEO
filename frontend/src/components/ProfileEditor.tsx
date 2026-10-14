"use client";

import { type IdeaProfile, REGIONS, REQUIRED_FIELDS } from "@/lib/idea";

type FieldDef = { key: keyof IdeaProfile; label: string; placeholder: string; rows?: number };

// 1차 분석(컨설턴트형)이 칸 안을 여러 줄로 나눠 채우므로, 이름 말고는 모두 여러 줄 입력칸
const GROUPS: { title: string; fields: FieldDef[] }[] = [
  {
    title: "아이템",
    fields: [
      { key: "name", label: "이름", placeholder: "예: 다문화 아동 한국어 학습 앱" },
      {
        key: "oneLiner",
        label: "한줄 소개",
        placeholder: "[첫 공략 고객]을 위한 [카테고리]. [기존 대안]과 달리 [차별점].",
        rows: 2,
      },
    ],
  },
  {
    title: "문제 · 고객",
    fields: [
      {
        key: "customer",
        label: "고객 정의",
        placeholder: "첫 공략: 구체적인 고객 한 그룹\n사용자 / 구매자: 쓰는 사람 / 돈 내는 사람",
        rows: 2,
      },
      {
        key: "problem",
        label: "고객 문제 정의",
        placeholder: "문제: 누가, 어떤 상황에서, 무엇 때문에, 그래서 어떤 결과가\n빈도·강도: 얼마나 자주, 얼마나 아픈지\n현재 대안: 지금 쓰는 방법 — 한계: 그 방법의 불만",
        rows: 5,
      },
    ],
  },
  {
    title: "해결 · 솔루션",
    fields: [
      {
        key: "solution",
        label: "문제 해결 방법",
        placeholder: "핵심 기능: 2~3개\n차별점: 현재 대안과 다른 점",
        rows: 4,
      },
      {
        key: "revenueModel",
        label: "수익 모델",
        placeholder: "구매자 · 방식 · 가격 가설 (모르면 비워둬도 돼요)",
        rows: 3,
      },
    ],
  },
];

const inputStyle = { border: "1.5px solid #E5E7EB" };

interface Props {
  value: IdeaProfile;
  onChange: (next: IdeaProfile) => void;
  readOnly?: boolean;
}

export default function ProfileEditor({ value, onChange, readOnly }: Props) {
  function update(key: keyof IdeaProfile, v: string) {
    onChange({ ...value, [key]: v });
  }

  function label(key: keyof IdeaProfile, text: string) {
    // 라벨이 세로 flex라 글자와 별표를 한 덩어리로 묶는다
    return (
      <span>
        {text}
        {REQUIRED_FIELDS.includes(key) && <span style={{ color: "#B42318" }}> *</span>}
      </span>
    );
  }

  return (
    <div className="flex flex-col gap-7">
      {GROUPS.map((group, gi) => (
        <fieldset key={group.title} className="flex flex-col gap-4 border-0 p-0 m-0" disabled={readOnly}>
          <legend className="text-sm font-bold mb-3 p-0" style={{ color: "#7270FF" }}>
            {group.title}
          </legend>

          {group.fields.map((f) => (
            <label key={f.key} className="flex flex-col gap-1.5 text-sm font-semibold">
              {label(f.key, f.label)}
              {f.rows ? (
                <textarea
                  value={value[f.key]}
                  onChange={(e) => update(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  rows={f.rows}
                  className="rounded-lg p-4 font-normal text-sm resize-y focus:outline-none leading-relaxed disabled:bg-surface"
                  style={inputStyle}
                />
              ) : (
                <input
                  type="text"
                  value={value[f.key]}
                  onChange={(e) => update(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  className="h-12 rounded-lg px-4 font-normal text-sm focus:outline-none disabled:bg-surface"
                  style={inputStyle}
                />
              )}
            </label>
          ))}

          {/* 분야·지역은 상세 진단 검색어와 공고 매칭에 쓰이는 태그 */}
          {gi === 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                {label("industry", "분야")}
                <input
                  type="text"
                  value={value.industry}
                  onChange={(e) => update("industry", e.target.value)}
                  placeholder="예: 에듀테크, 반려동물"
                  className="h-12 rounded-lg px-4 font-normal text-sm focus:outline-none disabled:bg-surface"
                  style={inputStyle}
                />
              </label>
              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                지역
                <select
                  value={value.location}
                  onChange={(e) => update("location", e.target.value)}
                  className="h-12 rounded-lg px-4 font-normal text-sm focus:outline-none bg-white disabled:bg-surface"
                  style={inputStyle}
                >
                  {REGIONS.map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </select>
              </label>
            </div>
          )}
        </fieldset>
      ))}
    </div>
  );
}
