-- 서치 콘솔 검색 성과(검색어×페이지×날짜). 서비스 키로만 쓰고, 읽기는 아래 보안 정의 함수로만 한다(RLS 켜고 정책 없음).
create table if not exists public.gsc_perf_daily (
  day date not null,
  page text not null,
  query text not null,
  clicks integer not null default 0,
  impressions integer not null default 0,
  position numeric(6,2),
  primary key (day, page, query)
);
alter table public.gsc_perf_daily enable row level security;
revoke all on public.gsc_perf_daily from anon, authenticated;
create index if not exists gsc_perf_daily_page_idx on public.gsc_perf_daily (page, day);

-- 기간 합계(전·후 비교용). 제목·설명을 바꾼 페이지 묶음의 CTR 변화를 볼 때 쓴다.
create or replace function public.gsc_ctr_window(p_prefix text, p_from date, p_to date)
returns jsonb language sql security definer set search_path = public as $$
  select jsonb_build_object(
    'from', p_from, 'to', p_to, 'prefix', p_prefix,
    'clicks', coalesce(sum(clicks), 0),
    'impressions', coalesce(sum(impressions), 0),
    'ctr_pct', case when coalesce(sum(impressions), 0) = 0 then null
                    else round(100.0 * sum(clicks) / sum(impressions), 2) end,
    'avg_position', round((sum(position * impressions) / nullif(sum(impressions), 0))::numeric, 1))
  from gsc_perf_daily
  where day between p_from and p_to and page like p_prefix || '%';
$$;
revoke all on function public.gsc_ctr_window(text, date, date) from public, anon, authenticated;

-- 개선 기회: (1) 노출은 있는데 클릭이 적은 페이지(제목·설명 개선 후보)
--            (2) 2~3쪽(평균 8~30위)에 걸린 검색어(본문·제목 보강 후보, 키워드 갭)
--            (3) 최근 7일 대 직전 7일 합계
-- 표본이 작을 때 헛경보를 막으려고 노출 기준을 둔다(페이지 20회, 검색어 10회).
create or replace function public.gsc_opportunities(p_days integer default 28)
returns jsonb language sql security definer set search_path = public as $$
  with w as (
    select * from gsc_perf_daily where day >= current_date - p_days
  ),
  pg as (
    select page, sum(clicks) c, sum(impressions) i,
           sum(position * impressions) / nullif(sum(impressions), 0) pos
    from w group by page
  ),
  top_q as (
    select distinct on (page) page, query from w order by page, impressions desc
  ),
  qy as (
    select query, sum(clicks) c, sum(impressions) i,
           sum(position * impressions) / nullif(sum(impressions), 0) pos
    from w group by query
  ),
  best as (
    select distinct on (query) query, page from w order by query, impressions desc
  ),
  cur as (select coalesce(sum(clicks),0) c, coalesce(sum(impressions),0) i from gsc_perf_daily where day >= current_date - 7),
  prv as (select coalesce(sum(clicks),0) c, coalesce(sum(impressions),0) i from gsc_perf_daily where day >= current_date - 14 and day < current_date - 7)
  select jsonb_build_object(
    'days', p_days,
    'rows', (select count(*) from w),
    'ctr_candidates', coalesce((
      select jsonb_agg(x) from (
        select jsonb_build_object('page', pg.page, 'impressions', pg.i, 'clicks', pg.c,
               'ctr_pct', round(100.0 * pg.c / pg.i, 2), 'avg_position', round(pg.pos::numeric, 1),
               'top_query', top_q.query) x
        from pg join top_q using (page)
        where pg.i >= 20 and pg.pos <= 20 and 100.0 * pg.c / pg.i < 3
        order by pg.i desc limit 15) s), '[]'::jsonb),
    'keyword_gaps', coalesce((
      select jsonb_agg(x) from (
        select jsonb_build_object('query', qy.query, 'impressions', qy.i, 'clicks', qy.c,
               'avg_position', round(qy.pos::numeric, 1), 'page', best.page) x
        from qy join best using (query)
        where qy.i >= 10 and qy.pos between 8 and 30
        order by qy.i desc limit 20) s), '[]'::jsonb),
    'last7', (select jsonb_build_object('clicks', c, 'impressions', i) from cur),
    'prev7', (select jsonb_build_object('clicks', c, 'impressions', i) from prv)
  );
$$;
revoke all on function public.gsc_opportunities(integer) from public, anon, authenticated;

-- 주간 스냅샷에 검색 성과 기회를 함께 남긴다.
create or replace function public.growth_snapshot() returns void language sql security definer set search_path = public as $$
  insert into growth_weekly(week_end, report)
  values (current_date - 1, growth_report(current_date - 1) || jsonb_build_object(
    'experiments', coalesce((select jsonb_agg(experiment_eval(id)) from growth_experiments where status = 'active'), '[]'::jsonb),
    'gsc', gsc_summary(),
    'gsc_perf', gsc_opportunities(28)))
  on conflict (week_end) do update set report = excluded.report, created_at = now();
$$;
revoke all on function public.growth_snapshot() from public, anon, authenticated;
