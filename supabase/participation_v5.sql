-- 참여 기능 5차: 닉네임 신고와 자동 가림. 2026-11-22
-- 서로 다른 로그인 사용자 3명이 같은 닉네임을 신고하면, 그 닉네임은 지점의 "처음 확인한 사람"으로 보이지 않는다(운영자가 확인할 때까지).
create table if not exists public.nickname_reports (
  reporter uuid not null references auth.users(id) on delete cascade,
  target uuid not null references auth.users(id) on delete cascade,
  route_id text not null check (route_id ~ '^(dr|ft|mt)-[A-Za-z0-9_-]{1,60}$'),
  poi_key text not null check (poi_key ~ '^[A-Z]{3,12}:[0-9]{1,7}(-[0-9]{1,7})?$'),
  created_at timestamptz not null default now(),
  primary key (reporter, target)
);
alter table public.nickname_reports enable row level security;
revoke all on table public.nickname_reports from anon, authenticated;
create index if not exists nickname_reports_target on public.nickname_reports (target);

-- 신고 대상은 클라이언트가 고르지 않는다: 그 지점에서 지금 "처음 확인한 사람"으로 보이는 닉네임에만 신고가 붙는다.
create or replace function public.report_nickname(p_route text, p_poi text) returns text language plpgsql security definer set search_path to 'public' as $$
declare uid uuid := auth.uid(); t uuid;
begin
  if uid is null then return 'login'; end if;
  if p_route !~ '^(dr|ft|mt)-[A-Za-z0-9_-]{1,60}$' or p_poi !~ '^[A-Z]{3,12}:[0-9]{1,7}(-[0-9]{1,7})?$' then return 'bad'; end if;
  if (select count(*) from public.nickname_reports where reporter = uid and created_at > now() - interval '1 hour') >= 10 then return 'slow'; end if;
  select f.user_id into t from public.poi_checks f join public.profiles p on p.id = f.user_id
   where f.route_id = p_route and f.poi_key = p_poi and f.answer = 'yes' and p.display_name is not null
     and not exists (select 1 from public.nickname_reports r where r.target = f.user_id group by r.target having count(*) >= 3)
   order by f.first_at limit 1;
  if t is null then return 'none'; end if;
  if t = uid then return 'self'; end if;
  insert into public.nickname_reports (reporter, target, route_id, poi_key) values (uid, t, p_route, p_poi) on conflict (reporter, target) do nothing;
  return 'ok';
end $$;
revoke all on function public.report_nickname(text, text) from public, anon;
grant execute on function public.report_nickname(text, text) to authenticated;

create or replace function public.poi_check_summary(p_route text) returns table(poi_key text, yes_n int, no_n int, last_at timestamptz, first_name text) language sql stable security definer set search_path to 'public' as $$
  select c.poi_key,
    (count(*) filter (where c.answer = 'yes' and c.checked_at > now() - interval '180 days'))::int,
    (count(*) filter (where c.answer = 'no' and c.checked_at > now() - interval '180 days'))::int,
    max(c.checked_at),
    (select p.display_name from public.poi_checks f join public.profiles p on p.id = f.user_id
       where f.route_id = c.route_id and f.poi_key = c.poi_key and f.answer = 'yes' and p.display_name is not null
         and not exists (select 1 from public.nickname_reports r where r.target = f.user_id group by r.target having count(*) >= 3)
       order by f.first_at limit 1)
  from public.poi_checks c where c.route_id = p_route group by c.route_id, c.poi_key;
$$;
