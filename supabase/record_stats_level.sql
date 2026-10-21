-- =====================================================================
-- record_stats 수정 — 등급표 화면에서도 기록을 보탤 수 있게
--
-- 왜
--   동의를 묻는 자리가 기록증 화면에만 있었습니다. 거기까지 가려면
--   사진을 올리고, 카드를 만들고, 동의하고, 버튼을 눌러야 합니다.
--   정작 사람들이 많이 오는 곳은 등급표 화면인데 거기엔 물을 자리가
--   없었습니다. 그래서 몇 달 동안 실제 데이터가 0건이었습니다.
--
--   등급표 화면에서는 기록만 칩니다 — 대회명을 받지 않습니다.
--   대회명을 필수로 둔 채로는 그 경로를 열 수 없어서 선택으로 바꿉니다.
--
-- 무엇이 달라지나
--   race_name 이 비어 있어도 됩니다. 대신 어느 경로로 들어왔는지
--   source 에 남겨서('cert' = 기록증, 'level' = 등급표),
--   나중에 대회별 분석이 필요할 때 기록증 쪽만 골라 쓸 수 있습니다.
--
-- 적용
--   Supabase 대시보드 → SQL Editor 에 붙여 넣고 실행하세요.
--   이미 들어온 줄은 건드리지 않습니다.
-- =====================================================================

-- 1) 대회명을 선택 항목으로
alter table public.record_stats
  alter column race_name drop not null;

-- 2) 길이 제약은 값이 있을 때만 따진다
alter table public.record_stats
  drop constraint if exists record_stats_race_name_len;

alter table public.record_stats
  add constraint record_stats_race_name_len
  check (race_name is null or char_length(race_name) between 1 and 120);

-- 3) 들어온 경로를 구분한다
alter table public.record_stats
  drop constraint if exists record_stats_source_known;

alter table public.record_stats
  add constraint record_stats_source_known
  check (source in ('cert', 'level', 'manual'));

-- 4) 대회명 없는 줄은 대회 날짜도 있을 수 없다 — 앞뒤가 맞게 막아 둔다
alter table public.record_stats
  drop constraint if exists record_stats_date_needs_race;

alter table public.record_stats
  add constraint record_stats_date_needs_race
  check (race_date is null or race_name is not null);

-- 확인용 — 지금 몇 건이 어느 경로로 들어와 있는지
select source, count(*) as 건수
from public.record_stats
group by source
order by source;
