-- 제주담 DB 스키마: Supabase 대시보드 > SQL Editor 에 붙여넣고 Run
-- 한 번만 실행하세요. (정책/트리거 이름이 중복되면 오류가 납니다)

-- 1) 프로필 -----------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  nickname text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles_select_own" on public.profiles
  for select to authenticated
  using ((select auth.uid()) = id);

create policy "profiles_insert_own" on public.profiles
  for insert to authenticated
  with check ((select auth.uid()) = id);

create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- 회원가입 시 프로필 자동 생성 (닉네임은 가입 폼의 nickname, 없으면 이메일 앞부분)
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, nickname)
  values (
    new.id,
    coalesce(nullif(new.raw_user_meta_data ->> 'nickname', ''), split_part(new.email, '@', 1))
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 2) 즐겨찾는 제주 명소 -------------------------------------------------
create table if not exists public.favorites (
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  spot_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, spot_id)
);

alter table public.favorites enable row level security;

create policy "favorites_select_own" on public.favorites
  for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "favorites_insert_own" on public.favorites
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "favorites_delete_own" on public.favorites
  for delete to authenticated
  using ((select auth.uid()) = user_id);
