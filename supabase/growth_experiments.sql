-- 실험 등록표와 전후 비교. 승인된 실험을 등록하면 주간 리포트가 시작 전 N일과 시작 후 N일을 같은 길이로 비교한다.
-- 지표: views(조회), visitors(방문자), events_per_view(조회당 클릭·다음 이동). 대상은 경로 접두어 목록.
-- 판정: 시작 후 14일 미만이면 pending, 시작 전 조회가 50 미만이면 표본 부족 표시.
--       증가 +20% 이상 keep, 감소 -10% 이하 drop, 그 사이 inconclusive.
create table if not exists public.growth_experiments (
  id serial primary key,
  name text not null,
  hypothesis text not null,
  target_prefixes text[] not null,
  metric text not null default 'views' check (metric in ('views','visitors','events_per_view')),
  start_date date not null,
  window_days int not null default 14 check (window_days between 7 and 60),
  status text not null default 'active' check (status in ('active','kept','dropped','closed')),
  created_at timestamptz not null default now()
);
alter table public.growth_experiments enable row level security;
revoke all on public.growth_experiments from anon, authenticated;

create or replace function public.experiment_eval(p_id int, p_today date default current_date)
returns jsonb language plpgsql security definer set search_path = public as $$
declare e growth_experiments%rowtype; win int; before_from date; before_to date; after_to date;
  b numeric; a numeric; bv numeric; av numeric; delta numeric; verdict text; small boolean;
begin
  select * into e from growth_experiments where id = p_id;
  if not found then return null; end if;
  win := least(e.window_days, greatest((p_today - e.start_date), 0));
  if win < 14 then
    return jsonb_build_object('id',e.id,'name',e.name,'verdict','pending','days_elapsed',(p_today - e.start_date));
  end if;
  before_from := e.start_date - win; before_to := e.start_date - 1; after_to := e.start_date + win - 1;

  select coalesce(sum(d.views),0), coalesce(sum(d.visitors),0) into bv, b from site_daily d
   where d.day between before_from and before_to and exists (select 1 from unnest(e.target_prefixes) p where d.path like p || '%');
  select coalesce(sum(d.views),0), coalesce(sum(d.visitors),0) into av, a from site_daily d
   where d.day between e.start_date and after_to and exists (select 1 from unnest(e.target_prefixes) p where d.path like p || '%');

  if e.metric = 'events_per_view' then
    b := case when bv > 0 then (select coalesce(sum(x.n),0) from site_evt x where x.day between before_from and before_to
          and exists (select 1 from unnest(e.target_prefixes) p where x.path like p || '%')) / bv else null end;
    a := case when av > 0 then (select coalesce(sum(x.n),0) from site_evt x where x.day between e.start_date and after_to
          and exists (select 1 from unnest(e.target_prefixes) p where x.path like p || '%')) / av else null end;
  elsif e.metric = 'views' then b := bv; a := av;
  end if;

  small := bv < 50;
  if b is null or a is null or b = 0 then delta := null; else delta := round((a - b) * 100.0 / b, 1); end if;
  verdict := case when delta is null then 'inconclusive' when delta >= 20 then 'keep' when delta <= -10 then 'drop' else 'inconclusive' end;
  return jsonb_build_object('id',e.id,'name',e.name,'metric',e.metric,'window_days',win,
    'before',round(b,3),'after',round(a,3),'delta_pct',delta,'verdict',verdict,'small_sample',small);
end $$;
revoke all on function public.experiment_eval(int, date) from public, anon, authenticated;
