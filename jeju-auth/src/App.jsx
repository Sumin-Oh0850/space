import { supabaseConfigured } from './lib/supabase'
import { useSession } from './hooks/useSession'
import { useHashRoute } from './hooks/useHashRoute'
import Header from './components/Header'
import Hero from './components/Hero'
import Spots from './components/Spots'
import AuthForm from './components/AuthForm'
import Profile from './components/Profile'
import Footer from './components/Footer'
import SetupNotice from './components/SetupNotice'

export default function App() {
  const [route, go] = useHashRoute()
  const { session, loading } = useSession()

  if (!supabaseConfigured) return <SetupNotice />
  if (loading) return <div className="splash">🍊</div>

  // 로그인 필요 페이지 보호 / 로그인 상태에서 로그인·가입 화면 접근 시 홈으로
  let view = route
  if (route === 'me' && !session) view = 'login'
  if ((route === 'login' || route === 'signup') && session) view = 'home'

  return (
    <>
      <Header session={session} route={view} go={go} />
      <main>
        {view === 'home' && (
          <>
            <Hero session={session} />
            <Spots session={session} go={go} />
          </>
        )}
        {(view === 'login' || view === 'signup') && <AuthForm key={view} mode={view} go={go} />}
        {view === 'me' && session && <Profile session={session} go={go} />}
      </main>
      <Footer />
    </>
  )
}
