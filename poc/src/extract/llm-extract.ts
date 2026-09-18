import { optionalOpenAiKey } from "../lib/assert-env.ts"
import { loadPasted } from "../domain/extract-paste.ts"
import type { Extraction } from "../domain/types.ts"

const SYSTEM_RULE = `당신은 구매 요청서에서 항목을 추출합니다.
원문에 없는 값을 만들지 마세요. 값이 없으면 null.
'다음 주' 같은 모호 표현을 날짜로 바꾸지 마세요.
사람 확정 칸을 채우지 마세요.
JSON만 출력하세요. 항목 배열의 각 원소는 항목ID, 원문값, 원문발췌, 표준명후보, 메모.`

export function llmAvailable(): boolean {
  return optionalOpenAiKey() !== null
}

export async function extractLlm(
  text: string,
  docId: string | null = null,
): Promise<Extraction> {
  const key = optionalOpenAiKey()
  if (!key) {
    throw new Error("VITE_OPENAI_API_KEY가 없습니다. 규칙 추출 또는 JSON 붙여넣기를 사용하세요.")
  }
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      temperature: 0,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: SYSTEM_RULE },
        { role: "user", content: `요청서:\n${text}` },
      ],
    }),
  })
  if (!response.ok) {
    throw new Error(`LLM 요청 실패 (${response.status}). 규칙 추출로 전환하세요.`)
  }
  const data = (await response.json()) as {
    choices: Array<{ message: { content: string } }>
  }
  const content = data.choices[0]?.message?.content
  if (!content) throw new Error("LLM 응답이 비었습니다.")
  const extraction = loadPasted(content, text, docId)
  return { ...extraction, backend: "llm" }
}
