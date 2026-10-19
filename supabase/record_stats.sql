-- =====================================================================
-- record_stats — 동의받은 기록만 모으는 통계 테이블
--
-- 왜 이 테이블이 필요한가
--   "내 기록이 상위 몇 %인가" 는 러너가 가장 많이 묻는 질문인데,
--   한국 러너의 기록 분포 데이터가 없으면 답할 수 없습니다.
--   타이밍 업체가 공개한 결과(실명·배번·기록)는 개인정보라
--   가져오지 않기로 했습니다. 그래서 남은 방법은 하나입니다 —
--   본인이 자기 기록을 직접 보태 주는 것.
--
-- 무엇을 담지 않는가
--   이름, 배번, 사진, 정확한 생년, 대회 순위, 로그인 계정 식별자.
--   기록증 사진은 브라우저 밖으로 나가지 않습니다. 여기 오는 것은
--   사진에서 읽어 사람이 확인한 값뿐입니다.
--
--   계정 식별자를 일부러 넣지 않았습니다. 그래서 어떤 줄이 누구 것인지
--   아무도 알 수 없고, 동시에 개별 삭제 요청도 들어줄 수 없습니다.
--   이 점을 동의받기 전에 반드시 알려야 합니다.
--
-- 적용
--   Supabase 대시보드 → SQL Editor 에 붙여 넣고 실행하세요.
-- =====================================================================

create table if not exists public.record_stats (
  id                  bigint generated always as identity primary key,
  race_name           text        not null,
  race_date           date,
  sport               text        not null default 'marathon',
  distance_category   text        not null,
  finish_time_seconds integer     not null,
  age_band            text        not null,
  gender              text        not null,
  source              text        not null default 'cert',
  created_at          timestamptz not null default now(),

  -- 말이 안 되는 값은 애초에 들어오지 못하게 막습니다
  constraint record_stats_time_sane
    check (finish_time_seconds between 300 and 54000),       -- 5분 ~ 15시간
  constraint record_stats_distance_known
    check (distance_category in ('5km', '10km', 'half', 'full')),
  constraint record_stats_gender_known
    check (gender in ('male', 'female')),
  constraint record_stats_age_band_known
    check (age_band in ('10대','20대','30대','40대','50대','60대','70대','80대 이상')),
  constraint record_stats_source_known
    check (source in ('cert', 'manual')),
  constraint record_stats_race_name_len
    check (char_length(race_name) between 1 and 120)
);

create index if not exists record_stats_cell_idx
  on public.record_stats (distance_category, gender, age_band);

-- ---------------------------------------------------------------------
-- 권한: 누구나 보탤 수는 있지만, 아무도 원본 줄을 읽을 수 없습니다.
-- select 정책을 만들지 않으면 RLS 가 기본으로 전부 막습니다.
-- ---------------------------------------------------------------------
alter table public.record_stats enable row level security;

drop policy if exists "누구나 자기 기록을 보탤 수 있다" on public.record_stats;
create policy "누구나 자기 기록을 보탤 수 있다"
  on public.record_stats for insert
  to anon, authenticated
  with check (true);

-- ---------------------------------------------------------------------
-- 분포 조회 — 표본이 모자라면 숫자를 내주지 않습니다.
--
-- 이게 이 파일에서 가장 중요한 부분입니다. 표본 세 건으로 "상위 12%"
-- 같은 말을 하면 그건 숫자를 지어내는 것이고, 지금까지 쌓은 신뢰가
-- 거기서 무너집니다. 그래서 약속이 아니라 함수가 막도록 해 두었습니다.
-- 표본 수는 항상 함께 돌려주니 화면에서 그대로 밝힐 수 있습니다.
-- ---------------------------------------------------------------------
create or replace function public.record_distribution(
  p_distance text,
  p_gender   text,
  p_age_band text
)
returns table (
  sample_count bigint,
  enough       boolean,
  p10 integer, p25 integer, p50 integer, p75 integer, p90 integer
)
language sql
stable
security definer
set search_path = public
as $$
  with cell as (
    select finish_time_seconds as t
      from public.record_stats
     where distance_category = p_distance
       and gender            = p_gender
       and age_band          = p_age_band
  ), agg as (
    select count(*) as n,
           percentile_cont(0.10) within group (order by t) as q10,
           percentile_cont(0.25) within group (order by t) as q25,
           percentile_cont(0.50) within group (order by t) as q50,
           percentile_cont(0.75) within group (order by t) as q75,
           percentile_cont(0.90) within group (order by t) as q90
      from cell
  )
  select n,
         n >= 30,
         case when n >= 30 then q10::integer end,
         case when n >= 30 then q25::integer end,
         case when n >= 30 then q50::integer end,
         case when n >= 30 then q75::integer end,
         case when n >= 30 then q90::integer end
    from agg;
$$;

revoke all on function public.record_distribution(text, text, text) from public;
grant execute on function public.record_distribution(text, text, text) to anon, authenticated;

-- ---------------------------------------------------------------------
-- 얼마나 모였는지 보는 용도. 개별 기록은 드러나지 않습니다.
-- ---------------------------------------------------------------------
create or replace function public.record_stats_progress()
returns table (distance_category text, gender text, age_band text,
               sample_count bigint, enough boolean)
language sql stable security definer set search_path = public
as $$
  select distance_category, gender, age_band, count(*), count(*) >= 30
    from public.record_stats
   group by 1, 2, 3
   order by 4 desc;
$$;

revoke all on function public.record_stats_progress() from public;
grant execute on function public.record_stats_progress() to anon, authenticated;
