import { supabase } from '../lib/supabase'

export default function Header({ session, route, go }) {
  const logout = async () => {
    await supabase.auth.signOut()
    go('home')
  }
  const nickname = session?.user?.user_metadata?.nickname || session?.user?.email?.split('@')[0]

  return (
    <header className="header">
      <a className="logo" href="#/" onClick={() => window.scrollTo({ top: 0 })}>
        <span className="logo-mark">🍊</span> 제주담
      </a>
      <nav className="nav">
        {session ? (
          <>
            <a className={route === 'me' ? 'active' : ''} href="#/me">{nickname} 님</a>
            <button className="btn ghost" onClick={logout}>로그아웃</button>
          </>
        ) : (
          <>
            <a className={route === 'login' ? 'active' : ''} href="#/login">로그인</a>
            <a className="btn primary" href="#/signup">회원가입</a>
          </>
        )}
      </nav>
    </header>
  )
}
