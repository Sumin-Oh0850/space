import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { authErrorMessage } from '../lib/errors'
import Spots from './Spots'

export default function Profile({ session, go }) {
  const user = session.user
  const [nickname, setNickname] = useState(user.user_metadata?.nickname || '')
  const [newPw, setNewPw] = useState('')
  const [msg, setMsg] = useState({ type: '', text: '' })

  useEffect(() => {
    let active = true
    supabase.from('profiles').select('nickname').eq('id', user.id).maybeSingle().then(({ data }) => {
      if (active && data?.nickname) setNickname(data.nickname)
    })
    return () => { active = false }
  }, [user.id])

  const saveProfile = async (e) => {
    e.preventDefault()
    const { error } = await supabase.from('profiles').upsert({ id: user.id, nickname: nickname.trim() })
    setMsg(error ? { type: 'err', text: '저장 실패: ' + error.message } : { type: 'ok', text: '닉네임을 저장했어요.' })
  }

  const changePw = async (e) => {
    e.preventDefault()
    if (newPw.length < 6) return setMsg({ type: 'err', text: '비밀번호는 6자 이상이어야 합니다.' })
    const { error } = await supabase.auth.updateUser({ password: newPw })
    if (error) setMsg({ type: 'err', text: authErrorMessage(error) })
    else { setNewPw(''); setMsg({ type: 'ok', text: '비밀번호를 변경했어요.' }) }
  }

  return (
    <div className="page">
      <section className="auth-box wide">
        <h2>내 정보</h2>
        <p className="muted">{user.email} · 가입일 {new Date(user.created_at).toLocaleDateString('ko-KR')}</p>

        <form onSubmit={saveProfile} className="inline">
          <label>닉네임
            <input value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={20} />
          </label>
          <button className="btn primary">저장</button>
        </form>

        <form onSubmit={changePw} className="inline">
          <label>새 비밀번호
            <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} placeholder="6자 이상" autoComplete="new-password" />
          </label>
          <button className="btn">변경</button>
        </form>

        {msg.text && <p className={`notice ${msg.type}`}>{msg.text}</p>}
      </section>

      <h2 className="page-title">❤️ 내가 저장한 제주</h2>
      <Spots session={session} go={go} onlyFavorites />
    </div>
  )
}
