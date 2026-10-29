import { useEffect, useState } from 'react'
import { SPOTS } from '../lib/spots'
import { supabase } from '../lib/supabase'
import { usePixabayImage } from '../hooks/usePixabayImage'

function SpotCard({ spot, liked, onToggle }) {
  const img = usePixabayImage(spot.q, { perPage: 5 })
  return (
    <article className="card">
      <div className="card-img" style={img ? { backgroundImage: `url(${img.url})` } : undefined}>
        {!img && <span className="card-ph">🌊</span>}
        <button
          className={`heart ${liked ? 'on' : ''}`}
          onClick={() => onToggle(spot.id)}
          aria-label={liked ? `${spot.name} 즐겨찾기 해제` : `${spot.name} 즐겨찾기`}
          title={liked ? '즐겨찾기 해제' : '즐겨찾기'}
        >
          {liked ? '❤️' : '🤍'}
        </button>
        {img && (
          <a className="credit sm" href={img.page} target="_blank" rel="noreferrer">
            📷 {img.user} · Pixabay
          </a>
        )}
      </div>
      <div className="card-body">
        <span className="tag">{spot.tag}</span>
        <h3>{spot.name}</h3>
        <p>{spot.desc}</p>
      </div>
    </article>
  )
}

export default function Spots({ session, go, onlyFavorites = false }) {
  const [favs, setFavs] = useState(new Set())
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (!session) { setFavs(new Set()); return }
    let active = true
    supabase.from('favorites').select('spot_id').then(({ data, error }) => {
      if (!active) return
      if (error) { setMsg('즐겨찾기를 불러오지 못했습니다. (schema.sql 을 실행했는지 확인하세요)'); return }
      setFavs(new Set(data.map((r) => r.spot_id)))
    })
    return () => { active = false }
  }, [session])

  const toggle = async (id) => {
    if (!session) { go('login'); return }
    setMsg('')
    const had = favs.has(id)
    const next = new Set(favs); had ? next.delete(id) : next.add(id); setFavs(next)   // 낙관적 갱신
    const { error } = had
      ? await supabase.from('favorites').delete().eq('spot_id', id)
      : await supabase.from('favorites').insert({ spot_id: id })
    if (error) { setFavs(favs); setMsg('저장에 실패했습니다: ' + error.message) }
  }

  const list = onlyFavorites ? SPOTS.filter((s) => favs.has(s.id)) : SPOTS
  return (
    <section className="section" id="spots">
      {!onlyFavorites && (
        <div className="section-head">
          <h2>제주 명소</h2>
          <p>{session ? '❤️를 눌러 내 리스트에 저장하세요.' : '로그인하면 ❤️로 명소를 저장할 수 있어요.'}</p>
        </div>
      )}
      {msg && <p className="notice err">{msg}</p>}
      {onlyFavorites && list.length === 0 && <p className="empty">아직 저장한 명소가 없어요. 홈에서 ❤️를 눌러 보세요.</p>}
      <div className="grid">
        {list.map((s) => <SpotCard key={s.id} spot={s} liked={favs.has(s.id)} onToggle={toggle} />)}
      </div>
    </section>
  )
}
