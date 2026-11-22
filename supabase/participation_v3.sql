-- 산 페이지 시설 확인: 코스(dr/ft)에 더해 산(mt-<산코드>)도 받는다. 산 지점 키는 좌표를 1e4로 반올림한 KIND:위도-경도.
alter table public.poi_checks drop constraint if exists poi_checks_route_id_check;
alter table public.poi_checks drop constraint if exists poi_checks_poi_key_check;
alter table public.poi_checks add constraint poi_checks_route_id_check check (route_id ~ '^(dr|ft|mt)-[A-Za-z0-9_-]{1,60}$');
alter table public.poi_checks add constraint poi_checks_poi_key_check check (poi_key ~ '^[A-Z]{3,12}:[0-9]{1,7}(-[0-9]{1,7})?$');

create or replace function public.submit_poi_check(p_route text, p_poi text, p_answer text, p_device text default null) returns text language plpgsql security definer set search_path to 'public' as $$
declare w text; uid uuid := auth.uid();
begin
  if p_answer not in ('yes','no') or p_route !~ '^(dr|ft|mt)-[A-Za-z0-9_-]{1,60}$' or p_poi !~ '^[A-Z]{3,12}:[0-9]{1,7}(-[0-9]{1,7})?$' then return 'bad'; end if;
  if uid is not null then w := 'u:' || uid::text;
  elsif p_device ~ '^[a-f0-9-]{16,40}$' then w := 'd:' || p_device;
  else return 'bad'; end if;
  if (select count(*) from public.poi_checks where who = w and checked_at > now() - interval '1 hour') >= 60 then return 'slow'; end if;
  insert into public.poi_checks (route_id, poi_key, who, user_id, answer) values (p_route, p_poi, w, uid, p_answer)
  on conflict (route_id, poi_key, who) do update set answer = excluded.answer, checked_at = now();
  return 'ok';
end $$;
revoke all on function public.submit_poi_check(text,text,text,text) from public;
grant execute on function public.submit_poi_check(text,text,text,text) to anon, authenticated;
