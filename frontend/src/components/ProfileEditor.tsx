"use client";

import { type IdeaProfile, REGIONS, REQUIRED_FIELDS } from "@/lib/idea";

type FieldDef = { key: keyof IdeaProfile; label: string; placeholder: string; multiline?: boolean };

const GROUPS: { title: string; fields: FieldDef[] }[] = [
  {
    title: "아이템",
    fields: [
      { key: "name", label: "이름", placeholder: "예: 다문화 아동 한국어 학습 앱" },
      { key: "oneLiner", label: "한줄 소개", placeholder: "누구의 어떤 문제를 어떻게 푸는지 한 문장으로" },
    ],
  },
  {
    title: "문제 · 고객",
    fields: [
      { key: "customer", label: "고객 정의", placeholder: "예: 한국어가 서툰 다문화 가정 초등학생과 담임 교사" },
      {
        key: "problem",
        label: "고객 문제 정의",
        placeholder: "누가, 언제, 무엇 때문에 불편한지",
        multiline: true,
      },
    ],
  },
  {
    title: "해결 · 솔루션",
    fields: [
      { key: "solution", label: "문제 해결 방법", placeholder: "서비스가 어떻게 작동하는지", multiline: true },
      { key: "revenueModel", label: "수익 모델", placeholder: "누가, 얼마를, 어떻게 내는지 (모르면 비워둬도 돼요)" },
    ],
  },
];

const inputStyle = { border: "1.5px solid #D9DCE1" };

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
          <legend className="text-sm font-bold mb-3 p-0" style={{ color: "#2F5BD3" }}>
            {group.title}
          </legend>

          {group.fields.map((f) => (
            <label key={f.key} className="flex flex-col gap-1.5 text-sm font-semibold">
              {label(f.key, f.label)}
              {f.multiline ? (
                <textarea
                  value={value[f.key]}
                  onChange={(e) => update(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  rows={3}
                  className="rounded-xl p-4 font-normal text-sm resize-y focus:outline-none leading-relaxed disabled:bg-surface"
                  style={inputStyle}
                />
              ) : (
                <input
                  type="text"
                  value={value[f.key]}
                  onChange={(e) => update(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  className="h-12 rounded-xl px-4 font-normal text-sm focus:outline-none disabled:bg-surface"
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
                  className="h-12 rounded-xl px-4 font-normal text-sm focus:outline-none disabled:bg-surface"
                  style={inputStyle}
                />
              </label>
              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                지역
                <select
                  value={value.location}
                  onChange={(e) => update("location", e.target.value)}
                  className="h-12 rounded-xl px-4 font-normal text-sm focus:outline-none bg-white disabled:bg-surface"
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
