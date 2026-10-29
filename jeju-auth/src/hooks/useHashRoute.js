import { useCallback, useEffect, useState } from 'react'

const ROUTES = ['login', 'signup', 'me']
const parse = () => {
  const h = window.location.hash.replace(/^#\/?/, '')
  return ROUTES.includes(h) ? h : 'home'
}

// 간단한 해시 라우터: #/login, #/signup, #/me (그 외는 홈)
// Supabase 이메일 인증 링크가 붙이는 #access_token=... 은 홈으로 처리됩니다.
export function useHashRoute() {
  const [route, setRoute] = useState(parse)

  useEffect(() => {
    const onChange = () => setRoute(parse())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  const go = useCallback((to) => {
    window.location.hash = to === 'home' ? '#/' : `#/${to}`
    window.scrollTo({ top: 0 })
  }, [])

  return [route, go]
}
