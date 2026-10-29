import { useEffect, useState } from 'react'
import { pixabayFirst } from '../lib/pixabay'

// 검색어 후보로 Pixabay 이미지 1장을 가져옵니다. (키가 없거나 실패하면 null)
export function usePixabayImage(queries, opts) {
  const [image, setImage] = useState(null)
  const key = queries.join('|')

  useEffect(() => {
    let active = true
    pixabayFirst(queries, opts).then((img) => { if (active) setImage(img) })
    return () => { active = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return image
}
