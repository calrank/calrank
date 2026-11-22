-- 유입 출처를 페이지별로도 센다(날짜·페이지·출처 숫자만). "어느 페이지가 네이버/구글에서 왔는지"를 알기 위한 것.
create table if not exists public.site_page_src (
  day date not null, path text not null, src text not null, sessions integer not null default 0,
  primary key (day, path, src)
);
alter table public.site_page_src enable row level security;
revoke all on table public.site_page_src from anon, authenticated;

-- 기존 track_ref(text) 를 p_path 가 선택 인자인 하나의 함수로 바꾼다(겹쳐 두면 호출이 모호해진다).
drop function if exists public.track_ref(text);
create or replace function public.track_ref(p_src text, p_path text default null)
returns void language plpgsql security definer set search_path to 'public' as $$
declare
  d date := (now() at time zone 'Asia/Seoul')::date;
  s text := lower(coalesce(p_src, 'other'));
  p text := left(coalesce(p_path, ''), 120);
begin
  if s not in ('direct','naver','google','daum','kakao','instagram','facebook','youtube','x','threads','band','cafe','blog','share','other') then
    s := 'other';
  end if;
  insert into site_ref (day, src, sessions) values (d, s, 1)
  on conflict (day, src) do update set sessions = site_ref.sessions + 1;
  if p ~ '^/[A-Za-z0-9._/-]*$'
     and (exists (select 1 from site_page_src where day = d and path = p and src = s)
          or (select count(*) from site_page_src where day = d) < 3000) then
    insert into site_page_src (day, path, src, sessions) values (d, p, s, 1)
    on conflict (day, path, src) do update set sessions = site_page_src.sessions + 1;
  end if;
end $$;
revoke all on function public.track_ref(text, text) from public;
grant execute on function public.track_ref(text, text) to anon, authenticated;
