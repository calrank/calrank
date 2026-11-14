-- 유입 경로 집계(개인정보 없음). 하루·경로 종류별 숫자만 센다. 주소 전체는 저장하지 않는다.
-- src 는 아래 허용 목록의 값만 받는다. 세션당 한 번(들어온 첫 페이지)만 센다.
create table if not exists public.site_ref (
  day date not null,
  src text not null,
  sessions integer not null default 0,
  primary key (day, src)
);
alter table public.site_ref enable row level security;  -- 정책 없음: 직접 읽기/쓰기 불가

create or replace function public.track_ref(p_src text)
returns void language plpgsql security definer set search_path = public as $$
declare
  d date := (now() at time zone 'Asia/Seoul')::date;
  s text := lower(coalesce(p_src, 'other'));
begin
  if s not in ('direct','naver','google','daum','kakao','instagram','facebook','youtube','x','threads','band','cafe','blog','other') then
    s := 'other';
  end if;
  insert into site_ref (day, src, sessions) values (d, s, 1)
  on conflict (day, src) do update set sessions = site_ref.sessions + 1;
end $$;
revoke all on function public.track_ref(text) from public;
grant execute on function public.track_ref(text) to anon, authenticated;

-- 날짜 범위 합계만 내준다
create or replace function public.get_traffic_sources(p_days integer default 30)
returns table(src text, sessions bigint)
language sql stable security definer set search_path = public as $$
  select src, sum(sessions)::bigint
  from site_ref
  where day >= (now() at time zone 'Asia/Seoul')::date - greatest(1, least(coalesce(p_days, 30), 365))
  group by src order by 2 desc;
$$;
revoke all on function public.get_traffic_sources(integer) from public;
grant execute on function public.get_traffic_sources(integer) to anon, authenticated;
