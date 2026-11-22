-- 서치 콘솔 URL 검사 결과(매일 표본). 서비스 키로만 쓰고 읽는다(RLS 켜고 정책 없음).
create table if not exists public.gsc_index_daily (
  day date not null,
  url text not null,
  verdict text,            -- PASS / NEUTRAL / FAIL ...
  coverage text,           -- 예: "Submitted and indexed", "Discovered - currently not indexed"
  last_crawl timestamptz,
  google_canonical text,
  primary key (day, url)
);
alter table public.gsc_index_daily enable row level security;
revoke all on public.gsc_index_daily from anon, authenticated;

create or replace function public.gsc_summary() returns jsonb language sql security definer set search_path = public as $$
  with d as (select max(day) as day from gsc_index_daily),
  t as (select g.* from gsc_index_daily g, d where g.day = d.day)
  select coalesce(jsonb_build_object(
    'day', (select day from d),
    'inspected', (select count(*) from t),
    'indexed', (select count(*) from t where verdict = 'PASS'),
    'by_coverage', coalesce((select jsonb_object_agg(coverage, n) from (select coalesce(coverage,'(없음)') as coverage, count(*) n from t group by 1) x), '{}'::jsonb)
  ), '{}'::jsonb);
$$;
revoke all on function public.gsc_summary() from public, anon, authenticated;

create or replace function public.growth_snapshot() returns void language sql security definer set search_path = public as $$
  insert into growth_weekly(week_end, report)
  values (current_date - 1, growth_report(current_date - 1) || jsonb_build_object(
    'experiments', coalesce((select jsonb_agg(experiment_eval(id)) from growth_experiments where status = 'active'), '[]'::jsonb),
    'gsc', gsc_summary()))
  on conflict (week_end) do update set report = excluded.report, created_at = now();
$$;
revoke all on function public.growth_snapshot() from public, anon, authenticated;
