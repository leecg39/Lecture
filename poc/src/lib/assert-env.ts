export function optionalOpenAiKey(): string | null {
  const key = import.meta.env.VITE_OPENAI_API_KEY
  if (typeof key !== "string" || key.trim().length === 0) return null
  return key
}
