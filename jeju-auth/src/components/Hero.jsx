import { usePixabayImage } from '../hooks/usePixabayImage'

export default function Hero({ session }) {
  const img = usePixabayImage(['jeju island', 'jeju'], { perPage: 5 })

  return (
    <section className="hero" style={img ? { backgroundImage: `url(${img.large || img.url})` } : undefined}>
      <div className="hero-shade" />
      <div className="hero-inner">
        <p className="eyebrow">JEJU · 제주를 담다</p>
        <h1>바다와 오름, 그리고<br />주황빛 감귤의 섬</h1>
        <p className="lead">
          제주의 풍경을 둘러보고, 마음에 드는 명소를 ❤️로 저장해 보세요.
          회원이 되면 나만의 제주 리스트가 만들어져요.
        </p>
        <div className="cta">
          {session ? (
            <a className="btn primary lg" href="#/me">내 제주 리스트 보기</a>
          ) : (
            <>
              <a className="btn primary lg" href="#/signup">무료로 시작하기</a>
              <a className="btn ghost lg" href="#/login">로그인</a>
            </>
          )}
        </div>
      </div>
      {img && (
        <a className="credit" href={img.page} target="_blank" rel="noreferrer">
          📷 {img.user} · Pixabay
        </a>
      )}
    </section>
  )
}
