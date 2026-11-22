-- 참여 기능 6차: 이용자 장소 제보(지도에 없는 화장실·식수·쉼터·조망·위험 지점). 2026-11-22
-- 원칙: 현장(GPS)에서만 올릴 수 있고, 제보자 닉네임이 "처음 확인"으로 남고, 다른 이용자의 "있어요/없어요"로 바로잡힌다.
-- 제보 좌표 = 제보 순간의 GPS 위치(정확도 30m 이하). 같은 종류가 25m 안에 있으면 새로 만들지 않고 확인으로 처리한다.
create table if not exists public.poi_user (
  id bigint generated always as identity primary key,
  route_id text not null check (route_id ~ '^(dr|ft|mt)-[A-Za-z0-9_-]{1,60}$'),
  kind text not null check (kind in ('toilet','water','shelter','view','danger')),
  lat double precision not null check (lat between 33 and 38.7),
  lon double precision not null check (lon between 124.5 and 131.9),
  acc int not null check (acc between 0 and 30),
  note text check (note is null or char_length(note) <= 40),
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'live' check (status in ('live','hidden','removed')),  -- hidden: 투표로 자동 가림, removed: 제보자 삭제·운영자 제거
  hidden_at timestamptz,
  created_at timestamptz not null default now()
);
alter table public.poi_user enable row level security;
revoke all on table public.poi_user from anon, authenticated;
create index if not exists poi_user_route on public.poi_user (route_id) where status <> 'removed';
create index if not exists poi_user_owner on public.poi_user (user_id, created_at desc);

-- 확인 창: 위험은 90일, 그 밖은 180일 안의 기록만 센다. 점수는 "로그인한 서로 다른 사람"만 센다(기기 표만으로는 올리거나 가리지 못한다).
create or replace function public.poi_user_votes(p_id bigint, p_kind text) returns table(yes_u int, no_u int) language sql stable security definer set search_path to 'public' as $$
  select (count(distinct c.user_id) filter (where c.answer = 'yes'))::int, (count(distinct c.user_id) filter (where c.answer = 'no'))::int
  from public.poi_checks c
  where c.poi_key = 'USER:' || p_id and c.user_id is not null
    and c.checked_at > now() - (case when p_kind = 'danger' then interval '90 days' else interval '180 days' end);
$$;

-- 가림 규칙: 서로 다른 로그인 사용자 2명 이상이 "없어요"이고 "있어요"보다 많으면 가린다. 다시 "있어요"가 늘면 되살아난다. 운영자·제보자 삭제(removed)는 건드리지 않는다.
create or replace function public.poi_user_refresh(p_id bigint) returns void language plpgsql security definer set search_path to 'public' as $$
declare r public.poi_user; v record;
begin
  select * into r from public.poi_user where id = p_id;
  if not found or r.status = 'removed' then return; end if;
  select * into v from public.poi_user_votes(p_id, r.kind);
  if v.no_u >= 2 and v.no_u > v.yes_u then
    if r.status <> 'hidden' then update public.poi_user set status = 'hidden', hidden_at = now() where id = p_id; end if;
  elsif r.status = 'hidden' then
    update public.poi_user set status = 'live' where id = p_id;
  end if;
end $$;

-- 기존 확인 함수: 이용자 제보 지점(USER:번호)이면 확인 뒤 가림 규칙을 다시 계산한다.
create or replace function public.submit_poi_check(p_route text, p_poi text, p_answer text, p_device text default null) returns text language plpgsql security definer set search_path to 'public' as $$
declare w text; uid uuid := auth.uid();
begin
  if p_answer not in ('yes','no') or p_route !~ '^(dr|ft|mt)-[A-Za-z0-9_-]{1,60}$' or p_poi !~ '^[A-Z]{3,12}:[0-9]{1,7}(-[0-9]{1,7})?$' then return 'bad'; end if;
  if uid is not null then w := 'u:' || uid::text;
  elsif p_device ~ '^[a-f0-9-]{16,40}$' then w := 'd:' || p_device;
  else return 'bad'; end if;
  if p_poi ~ '^USER:[0-9]+$' and not exists (select 1 from public.poi_user where id = substr(p_poi, 6)::bigint and route_id = p_route and status <> 'removed') then return 'bad'; end if;
  if (select count(*) from public.poi_checks where who = w and checked_at > now() - interval '1 hour') >= 60 then return 'slow'; end if;
  insert into public.poi_checks (route_id, poi_key, who, user_id, answer) values (p_route, p_poi, w, uid, p_answer)
  on conflict (route_id, poi_key, who) do update set answer = excluded.answer, checked_at = now();
  if p_poi ~ '^USER:[0-9]+$' then perform public.poi_user_refresh(substr(p_poi, 6)::bigint); end if;
  return 'ok';
end $$;

-- 새 장소 제보. 반환: login | nick | bad | region | accuracy | blocked | slow | limit | ok:USER:번호 | dup:키
create or replace function public.submit_poi_user(p_route text, p_kind text, p_lat double precision, p_lon double precision, p_acc int, p_note text default null) returns text language plpgsql security definer set search_path to 'public' as $$
declare uid uuid := auth.uid(); n text := nullif(trim(regexp_replace(coalesce(p_note,''), '[[:cntrl:]]', ' ', 'g')), ''); d record; nid bigint; w text;
begin
  if uid is null then return 'login'; end if;
  if p_route !~ '^(dr|ft|mt)-[A-Za-z0-9_-]{1,60}$' or p_kind not in ('toilet','water','shelter','view','danger') or p_lat is null or p_lon is null or p_acc is null then return 'bad'; end if;
  if p_lat not between 33 and 38.7 or p_lon not between 124.5 and 131.9 then return 'region'; end if;
  if p_acc < 0 or p_acc > 30 then return 'accuracy'; end if;
  if n is not null and (char_length(n) > 40 or public.nickname_blocked(n) or n ~* '(https?://|www\.|[a-z0-9.-]+\.(com|net|kr|io|me)\b|[0-9]{2,4}-[0-9]{3,4}-[0-9]{4}|@)') then return 'bad'; end if;
  if not exists (select 1 from public.profiles where id = uid and display_name is not null) then return 'nick'; end if;
  if (select count(*) from public.poi_user where user_id = uid and status = 'hidden' and hidden_at > now() - interval '7 days') >= 3 then return 'blocked'; end if;
  -- 같은 종류가 25m 안에 이미 있으면 새로 만들지 않고 "있어요" 확인으로 처리한다.
  select u.id, u.kind into d from public.poi_user u
   where u.route_id = p_route and u.kind = p_kind and u.status <> 'removed'
     and sqrt(power((u.lon - p_lon) * 111320 * cos(radians(p_lat)), 2) + power((u.lat - p_lat) * 111320, 2)) < 25
   order by sqrt(power((u.lon - p_lon) * 111320 * cos(radians(p_lat)), 2) + power((u.lat - p_lat) * 111320, 2)) limit 1;
  if found then
    w := 'u:' || uid::text;
    insert into public.poi_checks (route_id, poi_key, who, user_id, answer) values (p_route, 'USER:' || d.id, w, uid, 'yes')
    on conflict (route_id, poi_key, who) do update set answer = 'yes', checked_at = now();
    perform public.poi_user_refresh(d.id);
    return 'dup:USER:' || d.id;
  end if;
  if exists (select 1 from public.poi_user where user_id = uid and created_at > now() - interval '1 minute') then return 'slow'; end if;
  if (select count(*) from public.poi_user where user_id = uid and created_at > now() - interval '24 hours') >= 5 then return 'limit'; end if;
  insert into public.poi_user (route_id, kind, lat, lon, acc, note, user_id) values (p_route, p_kind, round(p_lat::numeric, 5), round(p_lon::numeric, 5), p_acc, n, uid) returning id into nid;
  insert into public.poi_checks (route_id, poi_key, who, user_id, answer) values (p_route, 'USER:' || nid, 'u:' || uid::text, uid, 'yes');
  return 'ok:USER:' || nid;
end $$;

-- 지도에 올릴 제보 목록. 위험은 서로 다른 2명이 확인해야 모두에게 보이고, 제보자 본인에게는 바로 보인다.
create or replace function public.poi_user_list(p_route text) returns table(id bigint, kind text, lat double precision, lon double precision, note text, mine boolean) language sql stable security definer set search_path to 'public' as $$
  select u.id, u.kind, u.lat, u.lon, u.note, (u.user_id = auth.uid())
  from public.poi_user u cross join lateral public.poi_user_votes(u.id, u.kind) v
  where u.route_id = p_route and u.status = 'live' and v.yes_u - v.no_u >= 1
    and (u.kind <> 'danger' or v.yes_u >= 2 or u.user_id = auth.uid())
  order by u.id limit 300;
$$;

-- 내가 올린 제보(삭제용)
create or replace function public.my_poi_users() returns table(id bigint, route_id text, kind text, status text, note text, created_at timestamptz) language sql stable security definer set search_path to 'public' as $$
  select id, route_id, kind, status, note, created_at from public.poi_user where user_id = auth.uid() and status <> 'removed' order by created_at desc limit 100;
$$;

create or replace function public.delete_poi_user(p_id bigint) returns text language plpgsql security definer set search_path to 'public' as $$
declare uid uuid := auth.uid();
begin
  if uid is null then return 'login'; end if;
  update public.poi_user set status = 'removed' where id = p_id and user_id = uid and status <> 'removed';
  if not found then return 'none'; end if;
  return 'ok';
end $$;

revoke all on function public.poi_user_votes(bigint, text), public.poi_user_refresh(bigint), public.submit_poi_user(text, text, double precision, double precision, int, text), public.poi_user_list(text), public.my_poi_users(), public.delete_poi_user(bigint), public.submit_poi_check(text, text, text, text) from public, anon, authenticated;
grant execute on function public.submit_poi_check(text, text, text, text), public.poi_user_list(text) to anon, authenticated;
grant execute on function public.submit_poi_user(text, text, double precision, double precision, int, text), public.my_poi_users(), public.delete_poi_user(bigint) to authenticated;
