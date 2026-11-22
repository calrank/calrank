-- 영향 피드백: 내가 확인한 코스별로 "처음 확인한 날 이후 그 코스 페이지를 방문한 사람 수"를 돌려준다.
-- 기존 방문 집계(site_daily)만 쓰며, 로그인한 본인의 확인 기록에 대해서만 값이 나온다.
create or replace function public.my_impact() returns table(route_id text, since_day date, visitors bigint, checks bigint) language sql stable security definer set search_path to 'public' as $f$
  with m as (select p.route_id, min(p.first_at) f, count(*) n from public.poi_checks p where p.user_id = auth.uid() group by p.route_id)
  select m.route_id, (m.f at time zone 'Asia/Seoul')::date,
         coalesce((select sum(d.visitors) from public.site_daily d where d.path = case when m.route_id like 'mt-%' then '/mountain-' || substr(m.route_id, 4) || '.html' else '/course-' || m.route_id || '.html' end and d.day >= (m.f at time zone 'Asia/Seoul')::date), 0)::bigint, m.n
  from m order by m.f desc;
$f$;
revoke all on function public.my_impact() from public, anon;
grant execute on function public.my_impact() to authenticated;
