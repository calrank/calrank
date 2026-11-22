-- 2026-11-22: 외래키 색인 5개(성능 점검 권고). 동작은 바뀌지 않는다.
create index if not exists event_reviews_user_id_idx on public.event_reviews (user_id);
create index if not exists event_saves_user_id_idx on public.event_saves (user_id);
create index if not exists event_submissions_submitted_by_idx on public.event_submissions (submitted_by);
create index if not exists official_records_claimed_by_idx on public.official_records (claimed_by_user_id);
create index if not exists personal_records_user_id_idx on public.personal_records (user_id);
-- 남은 권고: RLS 정책의 auth.uid() 를 (select auth.uid()) 로 바꾸기(16개). 행이 수만 건이 넘을 때 효과가 있어 지금은 미룬다.
