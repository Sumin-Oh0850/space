import { useState } from 'react'
import { supabase } from '../lib/supabase'
import { authErrorMessage } from '../lib/errors'

export default function AuthForm({ mode, go }) {
  const isSignup = mode === 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [nickname, setNickname] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setInfo('')
    if (isSignup) {
      if (password.length < 6) return setError('비밀번호는 6자 이상이어야 합니다.')
      if (password !== password2) return setError('비밀번호 확인이 일치하지 않습니다.')
    }
    setBusy(true)
    try {
      if (isSignup) {
        const { data, error: err } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { nickname: nickname.trim() },
            emailRedirectTo: window.location.origin,   // Supabase > Auth > URL Configuration 의 Redirect URLs 에 등록 필요
          },
        })
        if (err) throw err
        // 이메일 확인이 켜져 있고 이미 가입된 이메일이면 identities 가 비어서 돌아옵니다.
        if (data.user && data.user.identities && data.user.identities.length === 0) {
          throw new Error('User already registered')
        }
        if (data.session) { go('home') }            // 이메일 확인을 끈 경우: 바로 로그인됨
        else setInfo('인증 메일을 보냈어요. 메일함에서 링크를 누르면 가입이 완료됩니다.')
      } else {
        const { error: err } = await supabase.auth.signInWithPassword({ email, password })
        if (err) throw err
        go('home')
      }
    } catch (err) {
      setError(authErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const reset = async () => {
    setError(''); setInfo('')
    if (!email) return setError('비밀번호를 재설정할 이메일을 먼저 입력해 주세요.')
    const { error: err } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: window.location.origin })
    if (err) setError(authErrorMessage(err)); else setInfo('비밀번호 재설정 메일을 보냈어요.')
  }

  return (
    <section className="auth">
      <form className="auth-box" onSubmit={submit}>
        <h2>{isSignup ? '제주담 회원가입' : '다시 만나서 반가워요'}</h2>
        <p className="muted">{isSignup ? '이메일과 비밀번호만으로 간단하게 시작하세요.' : '로그인하고 내 제주 리스트를 확인하세요.'}</p>

        {isSignup && (
          <label>닉네임
            <input value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="예: 감귤러버" maxLength={20} />
          </label>
        )}
        <label>이메일
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" />
        </label>
        <label>비밀번호
          <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="6자 이상" autoComplete={isSignup ? 'new-password' : 'current-password'} />
        </label>
        {isSignup && (
          <label>비밀번호 확인
            <input type="password" required value={password2} onChange={(e) => setPassword2(e.target.value)} autoComplete="new-password" />
          </label>
        )}

        {error && <p className="notice err">{error}</p>}
        {info && <p className="notice ok">{info}</p>}

        <button className="btn primary lg block" disabled={busy}>
          {busy ? '처리 중…' : isSignup ? '가입하기' : '로그인'}
        </button>

        {!isSignup && <button type="button" className="link" onClick={reset}>비밀번호를 잊으셨나요?</button>}
        <p className="switch">
          {isSignup ? <>이미 계정이 있나요? <a href="#/login">로그인</a></> : <>처음이신가요? <a href="#/signup">회원가입</a></>}
        </p>
      </form>
    </section>
  )
}
