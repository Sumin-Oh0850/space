// Pixabay API (https://pixabay.com/api/docs/)
// - 결과는 24시간 캐시(API 이용 안내 권장 사항)
// - 이미지를 보여줄 때는 출처(Pixabay, 작가) 표기를 함께 합니다.
const KEY = import.meta.env.VITE_PIXABAY_API_KEY
const TTL = 24 * 60 * 60 * 1000

export const pixabayConfigured = Boolean(KEY)

export async function pixabaySearch(query, { perPage = 5, orientation = 'horizontal' } = {}) {
  if (!KEY) return []
  const cacheKey = `pixabay:${query}:${orientation}:${perPage}`
  try {
    const cached = JSON.parse(localStorage.getItem(cacheKey) || 'null')
    if (cached && Date.now() - cached.t < TTL) return cached.v
  } catch { /* 캐시 읽기 실패는 무시 */ }

  const params = new URLSearchParams({
    key: KEY,
    q: query,
    image_type: 'photo',
    orientation,
    safesearch: 'true',
    order: 'popular',
    per_page: String(perPage),
    lang: 'en',
  })
  try {
    const res = await fetch(`https://pixabay.com/api/?${params}`)
    if (!res.ok) return []
    const json = await res.json()
    const hits = (json.hits || []).map((h) => ({
      id: h.id,
      url: h.webformatURL,
      large: h.largeImageURL,
      page: h.pageURL,
      user: h.user,
      tags: h.tags,
    }))
    try { localStorage.setItem(cacheKey, JSON.stringify({ t: Date.now(), v: hits })) } catch { /* 용량 초과 무시 */ }
    return hits
  } catch {
    return []
  }
}

// 후보 검색어를 순서대로 시도해서 첫 번째 이미지를 돌려줍니다.
export async function pixabayFirst(queries, opts) {
  for (const q of queries) {
    const hits = await pixabaySearch(q, opts)
    if (hits.length) return hits[0]
  }
  return null
}
