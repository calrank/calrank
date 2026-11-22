-- 참여 기능 1차 (닉네임 + 시설 지점 확인). 적용 전에 검토용. 2026-11-22
-- 1) 개인정보: 이메일 앞부분을 공개 이름으로 쓰지 않는다
create or replace function public.handle_new_user() returns trigger language plpgsql security definer set search_path to 'public' as $$
begin
  insert into public.profiles (id, display_name) values (new.id, null);
  return new;
end; $$;

update public.profiles p set display_name = null from auth.users u where u.id = p.id and p.display_name = split_part(u.email,'@',1);

drop policy if exists "profiles are viewable by everyone" on public.profiles;
create policy "users can read own profile" on public.profiles for select using (auth.uid() = id);

-- 2) 닉네임: 형식·중복 제한, 직접 수정 금지(함수로만)
alter table public.profiles add column if not exists nickname_set_at timestamptz;
alter table public.profiles drop constraint if exists display_name_format;
alter table public.profiles add constraint display_name_format check (display_name is null or display_name ~ '^[가-힣A-Za-z0-9_]{2,12}$');
create unique index if not exists profiles_display_name_lower on public.profiles (lower(display_name)) where display_name is not null;
revoke update on public.profiles from anon, authenticated;
grant update (profile_public) on public.profiles to authenticated;

create or replace function public.set_nickname(p_name text) returns text language plpgsql security definer set search_path to 'public' as $$
declare n text := trim(coalesce(p_name,''));
begin
  if auth.uid() is null then return 'login'; end if;
  if n !~ '^[가-힣A-Za-z0-9_]{2,12}$' then return 'format'; end if;
  if lower(n) in ('admin','administrator','guest','null','anonymous') or lower(n) like '%calrank%' or n like '%칼랭크%' or n like '%운영%' or n like '%관리자%' or n like '%사무국%' or n in ('익명','게스트') then return 'reserved'; end if;
  if exists (select 1 from public.profiles where id = auth.uid() and display_name is not null and nickname_set_at > now() - interval '7 days') then return 'too_soon'; end if;
  update public.profiles set display_name = n, nickname_set_at = now() where id = auth.uid();
  return 'ok';
exception when unique_violation then return 'taken';
end $$;

create or replace function public.nickname_available(p_name text) returns boolean language sql stable security definer set search_path to 'public' as $$
  select not exists (select 1 from public.profiles where lower(display_name) = lower(trim(p_name)));
$$;

-- 3) 시설 지점 확인(있어요/없어요): 테이블 직접 접근 금지, 함수로만
create table if not exists public.poi_checks (
  route_id text not null check (route_id ~ '^(dr|ft)-[A-Za-z0-9_-]{1,60}$'),
  poi_key text not null check (poi_key ~ '^[A-Z]{3,12}:[0-9]{1,6}$'),
  who text not null,
  user_id uuid references auth.users(id) on delete cascade,
  answer text not null check (answer in ('yes','no')),
  first_at timestamptz not null default now(),
  checked_at timestamptz not null default now(),
  primary key (route_id, poi_key, who)
);
alter table public.poi_checks enable row level security;
revoke all on table public.poi_checks from anon, authenticated;
create index if not exists poi_checks_user on public.poi_checks (user_id) where user_id is not null;

create or replace function public.submit_poi_check(p_route text, p_poi text, p_answer text, p_device text default null) returns text language plpgsql security definer set search_path to 'public' as $$
declare w text; uid uuid := auth.uid();
begin
  if p_answer not in ('yes','no') or p_route !~ '^(dr|ft)-[A-Za-z0-9_-]{1,60}$' or p_poi !~ '^[A-Z]{3,12}:[0-9]{1,6}$' then return 'bad'; end if;
  if uid is not null then w := 'u:' || uid::text;
  elsif p_device ~ '^[a-f0-9-]{16,40}$' then w := 'd:' || p_device;
  else return 'bad'; end if;
  if (select count(*) from public.poi_checks where who = w and checked_at > now() - interval '1 hour') >= 60 then return 'slow'; end if;
  insert into public.poi_checks (route_id, poi_key, who, user_id, answer) values (p_route, p_poi, w, uid, p_answer)
  on conflict (route_id, poi_key, who) do update set answer = excluded.answer, checked_at = now();
  return 'ok';
end $$;

create or replace function public.poi_check_summary(p_route text) returns table(poi_key text, yes_n int, no_n int, last_at timestamptz, first_name text) language sql stable security definer set search_path to 'public' as $$
  select c.poi_key,
    (count(*) filter (where c.answer = 'yes' and c.checked_at > now() - interval '180 days'))::int,
    (count(*) filter (where c.answer = 'no' and c.checked_at > now() - interval '180 days'))::int,
    max(c.checked_at),
    (select p.display_name from public.poi_checks f join public.profiles p on p.id = f.user_id
       where f.route_id = c.route_id and f.poi_key = c.poi_key and f.answer = 'yes' and p.display_name is not null order by f.first_at limit 1)
  from public.poi_checks c where c.route_id = p_route group by c.route_id, c.poi_key;
$$;

create or replace function public.my_poi_checks() returns table(route_id text, poi_key text, answer text, checked_at timestamptz) language sql stable security definer set search_path to 'public' as $$
  select route_id, poi_key, answer, checked_at from public.poi_checks where user_id = auth.uid() order by checked_at desc limit 500;
$$;

revoke all on function public.set_nickname(text), public.nickname_available(text), public.submit_poi_check(text,text,text,text), public.poi_check_summary(text), public.my_poi_checks() from public;
grant execute on function public.set_nickname(text), public.my_poi_checks() to authenticated;
grant execute on function public.nickname_available(text), public.submit_poi_check(text,text,text,text), public.poi_check_summary(text) to anon, authenticated;
