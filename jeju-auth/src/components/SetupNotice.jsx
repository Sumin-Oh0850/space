export default function SetupNotice() {
  return (
    <div className="setup">
      <h1>🔧 환경변수를 설정해 주세요</h1>
      <p><code>VITE_SUPABASE_URL</code> 과 <code>VITE_SUPABASE_ANON_KEY</code> 가 없습니다.</p>
      <ol>
        <li>로컬: <code>jeju-auth/.env</code> 파일을 만들고 값을 넣은 뒤 개발 서버를 다시 시작</li>
        <li>Vercel: Project Settings → Environment Variables 에 등록한 뒤 <b>Redeploy</b></li>
      </ol>
      <p className="muted">자세한 절차는 README.md 를 참고하세요.</p>
    </div>
  )
}
