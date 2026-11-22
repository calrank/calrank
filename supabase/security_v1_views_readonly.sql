-- 2026-11-22: 집계 뷰 3개는 읽기 전용으로만 연다(쓰기 권한 회수). 집계(5건 미만 숨김)를 위해 SECURITY DEFINER는 유지한다.
revoke all on public.record_stats_public, public.record_stats_pooled, public.record_stats_hist from anon, authenticated;
grant select on public.record_stats_public, public.record_stats_pooled, public.record_stats_hist to anon, authenticated;
