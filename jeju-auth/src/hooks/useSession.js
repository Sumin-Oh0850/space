import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

// 로그인 세션을 구독합니다. (새로고침해도 유지, 로그인/로그아웃 시 자동 갱신)
export function useSession() {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(Boolean(supabase))

  useEffect(() => {
    if (!supabase) return undefined
    let active = true
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return
      setSession(data.session)
      setLoading(false)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next)
      setLoading(false)
    })
    return () => {
      active = false
      sub.subscription.unsubscribe()
    }
  }, [])

  return { session, loading }
}
