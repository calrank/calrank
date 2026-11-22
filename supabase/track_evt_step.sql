-- 단계 이벤트(kind='step', target=단계 이름, path=발생한 페이지)를 받는다.
-- funnel.js 의 calrankMark(step) 가 track.js 의 calrankEvt 로 보낸다. 예: gq-calc, gq-save, aff-click.
create or replace function public.track_evt(p_path text, p_kind text, p_target text)
 returns void language plpgsql security definer set search_path to 'public' as $function$
declare
  d date := (now() at time zone 'Asia/Seoul')::date;
  p text := left(coalesce(p_path, '/'), 120);
  k text := lower(coalesce(p_kind, ''));
  t text := left(coalesce(p_target, ''), 80);
begin
  if p !~ '^/[A-Za-z0-9._/-]*$' then return; end if;
  if k not in ('next', 'click', 'map', 'hud', 'search', 'step') then return; end if;
  if t !~ '^[A-Za-z0-9._/#:-]*$' then t := 'other'; end if;
  if not exists (select 1 from site_evt where day = d and path = p and kind = k and target = t)
     and (select count(*) from site_evt where day = d) >= 5000 then
    return;
  end if;
  insert into site_evt (day, path, kind, target, n) values (d, p, k, t, 1)
  on conflict (day, path, kind, target) do update set n = site_evt.n + 1;
end $function$;
