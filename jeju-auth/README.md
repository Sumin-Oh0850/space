# 제주담 (jeju-auth)

제주를 소재로 한 사이트에 **Supabase 회원가입/로그인**을 붙인 Vite + React 프로젝트입니다.
사진은 **Pixabay API**, 배포는 **Vercel**을 기준으로 합니다.

- 회원가입 / 로그인 / 로그아웃 / 비밀번호 재설정 / 비밀번호 변경
- 로그인 후 제주 명소를 ❤️로 저장 (회원별 DB, RLS 적용)
- 내 정보에서 닉네임 수정

> 이 저장소는 `space` 저장소의 **`jeju-auth/` 폴더**에 들어 있습니다. (Vercel 배포 시 Root Directory 설정이 필요합니다 → 5단계)

---

## 환경변수 한눈에 보기

| 이름 | 어디서 얻나 | 공개 여부 |
|---|---|---|
| `VITE_SUPABASE_URL` | Supabase 프로젝트 URL | 브라우저에 노출됨(정상) |
| `VITE_SUPABASE_ANON_KEY` | Supabase **anon / publishable** 키 | 브라우저에 노출됨(정상, RLS로 보호) |
| `VITE_PIXABAY_API_KEY` | Pixabay API Key | 브라우저에 노출됨 |

> ⚠️ **`service_role`(secret) 키는 절대 `VITE_` 변수나 프런트 코드에 넣지 마세요.** 모든 보안 규칙을 우회합니다.
> `VITE_` 로 시작하는 변수만 브라우저 빌드에 포함되며, **빌드 시점에 코드에 박힙니다.** 값을 바꾸면 다시 빌드(재배포)해야 합니다.

---

## 1단계. Supabase 설정

1. https://supabase.com/dashboard 에서 프로젝트를 엽니다. (이미 만들어 둔 `Sumin-Oh0850's Project`)
2. **키 확인** — 화면 위 **Connect** 버튼, 또는 **Project Settings → API** 에서
   - **Project URL** → `VITE_SUPABASE_URL`
   - **anon public (또는 publishable) key** → `VITE_SUPABASE_ANON_KEY`
3. **DB 테이블 만들기** — 왼쪽 **SQL Editor → New query** 에 [`supabase/schema.sql`](supabase/schema.sql) 전체를 붙여넣고 **Run**.
   - `profiles`(닉네임), `favorites`(저장한 명소) 테이블과 RLS 정책, 가입 시 프로필 자동 생성 트리거가 만들어집니다.
   - 확인: **Database → Tables** 에 두 테이블이 보이면 성공 (지금은 Schema Visualizer가 비어 있습니다).
4. **이메일 로그인 설정** — **Authentication → Sign In / Providers → Email** 이 켜져 있는지 확인.
   - **Confirm email**(이메일 인증)을 켜 두면 가입 후 메일의 링크를 눌러야 로그인됩니다. 기본 제공 메일 발송은 **시간당 발송 한도가 낮아** 테스트가 막힐 수 있어요. 개발 중에는 꺼 두고, 실제 서비스 전에 켜거나 SMTP를 연결하세요.
5. **리다이렉트 주소 등록** — **Authentication → URL Configuration**
   - **Site URL**: 배포 후에는 Vercel 주소(`https://내프로젝트.vercel.app`), 개발 중에는 `http://localhost:5173`
   - **Redirect URLs** 에 둘 다 추가: `http://localhost:5173/**`, `https://내프로젝트.vercel.app/**`
   - 이메일 인증/비밀번호 재설정 링크가 이 주소로 돌아옵니다. 등록하지 않으면 링크가 동작하지 않습니다.

## 2단계. Pixabay API 키 받기

1. https://pixabay.com 에 가입/로그인
2. https://pixabay.com/api/docs/ 로 이동 — 로그인 상태면 문서 안에 **Your API key** 가 표시됩니다.
3. 그 값을 `VITE_PIXABAY_API_KEY` 로 사용합니다.
- 이용 안내: 결과는 24시간 캐시(코드에 구현됨), 사진 출처 표기(구현됨), 분당 호출 수 제한이 있습니다.
- 키가 없으면 사진 대신 그라데이션 배경이 표시되고 앱은 정상 동작합니다.

## 3단계. 로컬에서 실행

```bash
cd jeju-auth
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
# .env 를 열어 위에서 얻은 3개 값을 채웁니다
npm install
npm run dev                   # http://localhost:5173
```

테스트: 회원가입 → (이메일 인증을 켰다면 메일 링크 클릭) → 로그인 → 명소 ❤️ → 내 정보에서 확인.
Supabase 대시보드 **Authentication → Users** 에 계정이, **Table Editor** 에 `profiles`/`favorites` 행이 생깁니다.

## 4단계. GitHub에 올리기

이미 이 저장소에 포함되어 있습니다. 변경 후에는:

```bash
git add jeju-auth
git commit -m "Update jeju-auth"
git push
```

`.env` 는 `.gitignore` 로 제외되어 **올라가지 않습니다.** (`.env.example` 만 올라갑니다)

## 5단계. Vercel 배포

1. https://vercel.com → **Add New… → Project** → GitHub의 `space` 저장소 **Import**
2. **Root Directory** 를 **`jeju-auth`** 로 지정 (Edit 버튼) ← 중요
3. Framework Preset 은 **Vite** 로 자동 인식됩니다. (Build: `npm run build`, Output: `dist`)
4. **Environment Variables** 에 3개를 등록 (Name / Value, 환경은 Production·Preview·Development 모두 체크)
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_PIXABAY_API_KEY`
5. **Deploy**. 완료되면 발급된 주소(`https://….vercel.app`)를 확인합니다.
6. **다시 Supabase로 돌아가** 1단계의 5번(Site URL / Redirect URLs)에 이 주소를 등록합니다.
7. 환경변수를 나중에 바꿨다면 **Deployments → … → Redeploy** 로 다시 배포해야 반영됩니다.

## 폴더 구조

```
jeju-auth/
├─ supabase/schema.sql      # DB 테이블 + RLS (SQL Editor에서 1회 실행)
├─ src/
│  ├─ lib/                  # supabase 클라이언트, pixabay 호출, 명소 데이터, 오류 메시지
│  ├─ hooks/                # useSession(로그인 상태), useHashRoute, usePixabayImage
│  └─ components/           # Header, Hero, Spots, AuthForm, Profile, Footer
├─ .env.example
└─ vercel.json
```

## 자주 겪는 문제

| 증상 | 원인 / 해결 |
|---|---|
| "환경변수를 설정해 주세요" 화면 | `.env`(로컬) 또는 Vercel 환경변수 누락. 로컬은 서버 재시작, Vercel은 Redeploy |
| 가입 후 메일이 안 옴 | 기본 메일 한도 초과 가능. Confirm email 을 끄거나 SMTP 연결 |
| 인증 링크 클릭 시 오류/엉뚱한 주소 | Site URL / Redirect URLs 에 현재 주소 미등록 |
| 명소 ❤️ 저장 실패 | `schema.sql` 을 실행하지 않았거나 로그인이 풀림 |
| 사진이 안 나옴 | `VITE_PIXABAY_API_KEY` 누락, 호출 한도 초과, 검색 결과 없음 |
