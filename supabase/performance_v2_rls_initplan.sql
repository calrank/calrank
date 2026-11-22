-- RLS 정책 16개의 auth.uid() 를 (select auth.uid()) 로 감싼다.
-- 의미는 같고, 행마다 다시 계산하지 않고 한 번만 계산한다(Supabase 성능 점검 auth_rls_initplan).
do $$
declare r record; q text; w text; s text;
begin
  for r in select schemaname, tablename, policyname, qual, with_check from pg_policies
           where schemaname='public' and (coalesce(qual,'')||coalesce(with_check,'')) like '%auth.uid()%'
             and (coalesce(qual,'')||coalesce(with_check,'')) not like '%select auth.uid()%'
  loop
    q := replace(r.qual, 'auth.uid()', '(select auth.uid())');
    w := replace(r.with_check, 'auth.uid()', '(select auth.uid())');
    s := format('alter policy %I on %I.%I', r.policyname, r.schemaname, r.tablename);
    if q is not null then s := s || ' using (' || q || ')'; end if;
    if w is not null then s := s || ' with check (' || w || ')'; end if;
    execute s;
  end loop;
end $$;
