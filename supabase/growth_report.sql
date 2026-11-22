-- 주간 성장 리포트: 숫자만 모아 규칙 기반 발견 사항을 만든다. 개인 식별 정보는 쓰지 않는다.
-- growth_report(종료일) -> jsonb, growth_weekly 에 매주 월요일 06:30 KST(일요일 21:30 UTC)에 저장(pg_cron).
-- 서버 전용: anon/authenticated 실행 권한 없음. 운영자는 SQL 또는 주간 점검 작업이 읽는다.
create table if not exists public.growth_weekly (
  week_end date primary key,
  report jsonb not null,
  created_at timestamptz not null default now()
);
alter table public.growth_weekly enable row level security;
revoke all on public.growth_weekly from anon, authenticated;

create or replace function public.growth_report(p_end date default current_date)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  cur_from date := p_end - 6; prev_from date := p_end - 13; prev_to date := p_end - 7;
  v_cur bigint; v_prev bigint; u_cur bigint; u_prev bigint;
  findings jsonb := '[]'::jsonb; srcs jsonb; top jsonb; dead jsonb; contrib jsonb; evts jsonb;
  tot bigint; nv numeric; chg numeric;
begin
  select coalesce(sum(views),0), coalesce(sum(visitors),0) into v_cur, u_cur from site_daily where day between cur_from and p_end;
  select coalesce(sum(views),0), coalesce(sum(visitors),0) into v_prev, u_prev from site_daily where day between prev_from and prev_to;

  select coalesce(jsonb_object_agg(src, s), '{}') into srcs from
    (select src, sum(sessions) s from site_ref where day between cur_from and p_end group by src) x;
  select coalesce(sum(sessions),0) into tot from site_ref where day between cur_from and p_end;

  select coalesce(jsonb_agg(jsonb_build_object('path',path,'views',v,'visitors',u) order by v desc),'[]') into top from
    (select path, sum(views) v, sum(visitors) u from site_daily where day between cur_from and p_end and path not like '/\_f/%' group by path order by 3 desc limit 10) x;

  -- 조회는 20 이상인데 클릭 이벤트가 전혀 없는 페이지(다음 행동으로 이어지지 않는 후보)
  select coalesce(jsonb_agg(jsonb_build_object('path',path,'views',v) order by v desc),'[]') into dead from
    (select d.path, sum(d.views) v from site_daily d
      where d.day between cur_from and p_end and d.path not like '/\_f/%'
        and not exists (select 1 from site_evt e where e.day between cur_from and p_end and e.path = d.path)
      group by d.path having sum(d.views) >= 20 order by 2 desc limit 10) x;

  select coalesce(jsonb_object_agg(kind, n),'{}') into evts from
    (select kind, sum(n) n from site_evt where day between cur_from and p_end group by kind) x;

  select jsonb_build_object(
    'new_profiles', (select count(*) from profiles where created_at::date between cur_from and p_end),
    'reviews', (select count(*) from event_reviews where created_at::date between cur_from and p_end),
    'saves', (select count(*) from event_saves where created_at::date between cur_from and p_end),
    'records', (select count(*) from personal_records where created_at::date between cur_from and p_end),
    'submissions', (select count(*) from event_submissions where created_at::date between cur_from and p_end),
    'gear_uses', (select count(*) from gear_uses where created_at::date between cur_from and p_end)
  ) into contrib;

  if v_prev > 0 then
    chg := round((v_cur - v_prev) * 100.0 / v_prev, 1);
    findings := findings || jsonb_build_object('level', case when chg <= -30 then 'warn' else 'info' end,
      'text', format('방문 %s회(직전 주 %s회, %s%%), 방문자 %s명(직전 %s명)', v_cur, v_prev, chg, u_cur, u_prev));
  end if;
  if tot > 0 then
    nv := coalesce((srcs->>'naver')::numeric,0) * 100.0 / tot;
    if nv >= 60 then
      findings := findings || jsonb_build_object('level','warn',
        'text', format('네이버 비중 %s%%: 한 경로에 의존. 구글 색인·직접 재방문 확보가 과제', round(nv)));
    end if;
    if coalesce((srcs->>'google')::numeric,0) = 0 then
      findings := findings || jsonb_build_object('level','warn','text','구글 검색 유입 0건(색인 진행 전)');
    end if;
  end if;
  if jsonb_array_length(dead) > 0 then
    findings := findings || jsonb_build_object('level','info',
      'text', format('조회 20 이상인데 클릭이 없는 페이지 %s개: 다음 행동 링크 보강 후보. 최상위 %s', jsonb_array_length(dead), dead->0->>'path'));
  end if;
  if (contrib->>'reviews')::int + (contrib->>'records')::int + (contrib->>'saves')::int + (contrib->>'submissions')::int = 0 and u_cur >= 50 then
    findings := findings || jsonb_build_object('level','warn','text','이번 주 참여(후기·기록·저장·제보) 0건: 참여 유도 지점 점검 필요');
  end if;

  return jsonb_build_object('week_start', cur_from, 'week_end', p_end,
    'views', v_cur, 'visitors', u_cur, 'prev_views', v_prev, 'prev_visitors', u_prev,
    'sources', srcs, 'top_pages', top, 'no_action_pages', dead, 'events', evts,
    'contribution', contrib, 'findings', findings);
end $$;
revoke all on function public.growth_report(date) from public, anon, authenticated;

create or replace function public.growth_snapshot() returns void language sql security definer set search_path = public as $$
  insert into growth_weekly(week_end, report) values (current_date - 1, growth_report(current_date - 1))
  on conflict (week_end) do update set report = excluded.report, created_at = now();
$$;
revoke all on function public.growth_snapshot() from public, anon, authenticated;

-- 매주 일요일 21:30 UTC = 월요일 06:30 KST
-- create extension if not exists pg_cron;
-- select cron.schedule('growth-weekly', '30 21 * * 0', $$select public.growth_snapshot()$$);
