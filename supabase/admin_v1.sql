-- 운영자 검토: 운영자 계정만 이용자 장소 제보를 보고(가리기·복구·제거), 닉네임 신고를 확인한다. 2026-11-22
-- 운영자 지정(한 번): insert into public.admins select id from auth.users where email = '운영자 이메일';
create table if not exists public.admins (user_id uuid primary key references auth.users(id) on delete cascade, created_at timestamptz not null default now());
alter table public.admins enable row level security;
revoke all on table public.admins from anon, authenticated;

create or replace function public.is_admin() returns boolean language sql stable security definer set search_path to 'public' as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;

-- 제보 목록(최근순). 운영자가 아니면 빈 결과.
create or replace function public.admin_poi_list(p_status text default null) returns table(id bigint, route_id text, kind text, status text, note text, nick text, lat double precision, lon double precision, yes_u int, no_u int, created_at timestamptz) language sql stable security definer set search_path to 'public' as $$
  select u.id, u.route_id, u.kind, u.status, u.note, p.display_name, u.lat, u.lon, v.yes_u, v.no_u, u.created_at
  from public.poi_user u
  left join public.profiles p on p.id = u.user_id
  cross join lateral public.poi_user_votes(u.id, u.kind) v
  where public.is_admin() and (p_status is null or u.status = p_status)
  order by u.id desc limit 200;
$$;

-- 상태 변경: live(복구) / removed(제거). removed 는 투표 자동 규칙이 건드리지 않는다(자동 가림 hidden 은 투표가 바뀌면 되살아날 수 있다).
create or replace function public.admin_poi_set(p_id bigint, p_status text) returns text language plpgsql security definer set search_path to 'public' as $$
begin
  if not public.is_admin() then return 'denied'; end if;
  if p_status not in ('live','removed') then return 'bad'; end if;
  update public.poi_user set status = p_status where id = p_id;
  if not found then return 'none'; end if;
  return 'ok';
end $$;

-- 닉네임 신고 현황: 신고 대상 닉네임별 서로 다른 신고자 수(3명 이상이면 지점에서 닉네임이 가려진다).
create or replace function public.admin_nick_reports() returns table(target uuid, nick text, reporters int, last_at timestamptz) language sql stable security definer set search_path to 'public' as $$
  select r.target, p.display_name, count(distinct r.reporter)::int, max(r.created_at)
  from public.nickname_reports r left join public.profiles p on p.id = r.target
  where public.is_admin() group by r.target, p.display_name order by 3 desc, 4 desc limit 100;
$$;

revoke all on function public.is_admin(), public.admin_poi_list(text), public.admin_poi_set(bigint, text), public.admin_nick_reports() from public, anon, authenticated;
grant execute on function public.is_admin(), public.admin_poi_list(text), public.admin_poi_set(bigint, text), public.admin_nick_reports() to authenticated;
