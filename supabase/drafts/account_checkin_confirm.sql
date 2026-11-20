-- 초안: 아직 적용하지 않았다. 계정(닉네임)·체크인·시설 확인 표시용 테이블과 함수.
-- 적용 전에 Supabase 프로젝트에서 검토·시험이 필요하다(이 파일은 실행해 보지 않았다).
-- 원칙: 좌표는 저장하지 않는다. 지점 번호·종류·날짜만 저장한다. 본인 기록은 본인만 읽고 지운다.
-- 기존 방문 집계(track_evt)와 같은 방식: SECURITY DEFINER 함수 + 입력 제한 + 하루 상한.

-- 1) 프로필: 닉네임은 본인이 공개를 켠 경우에만 다른 사람에게 보인다.
create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  nickname text check (nickname is null or char_length(nickname) between 2 and 16),
  show_name boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.profiles enable row level security;
create policy profiles_own_select on public.profiles for select using (auth.uid() = user_id);
create policy profiles_own_upsert on public.profiles for insert with check (auth.uid() = user_id);
create policy profiles_own_update on public.profiles for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy profiles_own_delete on public.profiles for delete using (auth.uid() = user_id);

-- 2) 내 체크인(도장): 코스·정상 등을 다녀온 날. 기기에 쌓은 기록을 로그인할 때 합친다.
create table if not exists public.user_checkins (
  user_id uuid not null references auth.users(id) on delete cascade,
  kind text not null check (kind in ('course','peak','spot')),
  target text not null check (target ~ '^[a-z0-9:_@.\-]{1,60}$'),
  day date not null,
  created_at timestamptz not null default now(),
  primary key (user_id, kind, target, day)
);
alter table public.user_checkins enable row level security;
create policy checkins_own_all on public.user_checkins for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 3) 시설 확인 표시: 지점 번호·상태·날짜만. 같은 사람은 지점당 하루 한 번.
create table if not exists public.spot_confirms (
  user_id uuid not null references auth.users(id) on delete cascade,
  spot text not null check (spot ~ '^[a-z0-9:_@.\-]{1,60}$'),
  state text not null check (state in ('ok','missing','closed','no_water','moved')),
  day date not null,
  primary key (user_id, spot, day)
);
alter table public.spot_confirms enable row level security;
create policy confirms_own_all on public.spot_confirms for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 4) 지점별 집계: 누가 눌렀는지 없이 숫자만. 화면은 이 집계만 읽는다.
create table if not exists public.spot_confirm_daily (
  day date not null,
  spot text not null,
  state text not null,
  n int not null default 0,
  primary key (day, spot, state)
);
alter table public.spot_confirm_daily enable row level security;  -- 직접 읽기 정책 없음: 함수로만 접근

create or replace function public.confirm_spot(p_spot text, p_state text)
returns void language plpgsql security definer set search_path = public as $$
declare d date := (now() at time zone 'Asia/Seoul')::date; total int;
begin
  if auth.uid() is null then raise exception 'login required'; end if;
  if p_spot !~ '^[a-z0-9:_@.\-]{1,60}$' or p_state not in ('ok','missing','closed','no_water','moved') then return; end if;
  select coalesce(sum(n),0) into total from spot_confirm_daily where day = d;
  if total >= 5000 then return; end if;  -- 하루 상한
  insert into spot_confirms(user_id, spot, state, day) values (auth.uid(), p_spot, p_state, d) on conflict do nothing;
  if found then
    insert into spot_confirm_daily(day, spot, state, n) values (d, p_spot, p_state, 1)
    on conflict (day, spot, state) do update set n = spot_confirm_daily.n + 1;
  end if;
end $$;
revoke all on function public.confirm_spot(text, text) from public;
grant execute on function public.confirm_spot(text, text) to authenticated;

-- 5) 화면용 읽기: 지점별 최근 확인 요약(최근 날짜·상태별 인원). 사람 정보는 나오지 않는다.
create or replace function public.spot_summary(p_spot text)
returns table(state text, people bigint, last_day date) language sql security definer set search_path = public stable as $$
  select state, sum(n)::bigint, max(day) from spot_confirm_daily where spot = p_spot group by state;
$$;
grant execute on function public.spot_summary(text) to anon, authenticated;

-- 6) 계정 삭제(탈퇴) 시 on delete cascade 로 본인 기록이 함께 지워진다. 집계 숫자는 사람 정보가 없어 남는다.
-- 미정: '최초 확인 닉네임' 표시(2명 이상 확인 후 확정)는 profiles.show_name 을 켠 사람만, 별도 함수로 설계한다.
