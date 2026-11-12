-- 방문 통계(개인정보 없음). 하루·페이지 단위로 숫자만 센다.
create table if not exists public.site_daily (
  day date not null,
  path text not null,
  views integer not null default 0,
  visitors integer not null default 0,
  primary key (day, path)
);
alter table public.site_daily enable row level security;  -- 정책 없음: 직접 읽기/쓰기 불가

create or replace function public.track_view(p_path text, p_new boolean)
returns void language plpgsql security definer set search_path = public as $$
declare
  d date := (now() at time zone 'Asia/Seoul')::date;
  p text := left(coalesce(p_path, '/'), 120);
begin
  if p !~ '^/[A-Za-z0-9._/-]*$' then return; end if;
  -- 아무 경로나 계속 만들어 표를 부풀리는 것을 막는다: 하루 3000개를 넘으면 새 경로는 받지 않는다
  if not exists (select 1 from site_daily where day = d and path = p)
     and (select count(*) from site_daily where day = d) >= 3000 then
    return;
  end if;
  insert into site_daily (day, path, views, visitors)
  values (d, p, 1, case when p_new then 1 else 0 end)
  on conflict (day, path) do update
    set views = site_daily.views + 1,
        visitors = site_daily.visitors + case when p_new then 1 else 0 end;
end $$;
revoke all on function public.track_view(text, boolean) from public;
grant execute on function public.track_view(text, boolean) to anon, authenticated;

-- 소개 자료용: 날짜별 합계만 내준다(경로 없음)
create or replace function public.get_traffic_totals()
returns table(day date, views bigint, visitors bigint)
language sql stable security definer set search_path = public as $$
  select day, sum(views)::bigint, sum(visitors)::bigint
  from site_daily group by day order by day;
$$;
revoke all on function public.get_traffic_totals() from public;
grant execute on function public.get_traffic_totals() to anon, authenticated;
