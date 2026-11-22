-- 실험 안전장치: 겹침 금지, 동시 실험 수 상한, 대조군 보정.
alter table public.growth_experiments add column if not exists control_prefixes text[] not null default '{}';

-- 지표 하나를 기간·경로 접두어로 계산한다(조회·방문자·조회당 클릭).
create or replace function public.exp_metric(p_prefixes text[], p_from date, p_to date, p_metric text)
returns numeric language plpgsql security definer set search_path = public as $$
declare v numeric; u numeric; ev numeric;
begin
  select coalesce(sum(d.views),0), coalesce(sum(d.visitors),0) into v, u from site_daily d
   where d.day between p_from and p_to and exists (select 1 from unnest(p_prefixes) p where d.path like p || '%');
  if p_metric = 'views' then return v;
  elsif p_metric = 'visitors' then return u;
  else
    if v = 0 then return null; end if;
    select coalesce(sum(x.n),0) into ev from site_evt x
     where x.day between p_from and p_to and exists (select 1 from unnest(p_prefixes) p where x.path like p || '%');
    return ev / v;
  end if;
end $$;
revoke all on function public.exp_metric(text[], date, date, text) from public, anon, authenticated;

-- 등록 시 검사: 같은 지표로 진행 중인 실험과 대상 경로가 겹치면 거부, 진행 중 5개 초과 거부.
create or replace function public.growth_experiments_guard() returns trigger language plpgsql as $$
declare clash text; n int;
begin
  if new.status <> 'active' then return new; end if;
  select count(*) into n from growth_experiments where status = 'active' and id is distinct from new.id;
  if n >= 5 then raise exception '진행 중 실험은 5개까지입니다. 먼저 판정·종료하세요.'; end if;
  select e.name into clash from growth_experiments e
   where e.status = 'active' and e.id is distinct from new.id and e.metric = new.metric
     and exists (select 1 from unnest(e.target_prefixes) a, unnest(new.target_prefixes) b
                 where a like b || '%' or b like a || '%')
   limit 1;
  if clash is not null then raise exception '같은 지표로 대상이 겹치는 실험이 진행 중입니다: %', clash; end if;
  return new;
end $$;
drop trigger if exists growth_experiments_guard_t on public.growth_experiments;
create trigger growth_experiments_guard_t before insert on public.growth_experiments
  for each row execute function public.growth_experiments_guard();

create or replace function public.experiment_eval(p_id int, p_today date default current_date)
returns jsonb language plpgsql security definer set search_path = public as $$
declare e growth_experiments%rowtype; win int; bf date; bt date; at date;
  b numeric; a numeric; cb numeric; ca numeric; delta numeric; cdelta numeric; adj numeric;
  bv numeric; verdict text;
begin
  select * into e from growth_experiments where id = p_id;
  if not found then return null; end if;
  win := least(e.window_days, greatest((p_today - e.start_date), 0));
  if win < 14 then
    return jsonb_build_object('id',e.id,'name',e.name,'verdict','pending','days_elapsed',(p_today - e.start_date));
  end if;
  bf := e.start_date - win; bt := e.start_date - 1; at := e.start_date + win - 1;
  b := exp_metric(e.target_prefixes, bf, bt, e.metric);
  a := exp_metric(e.target_prefixes, e.start_date, at, e.metric);
  bv := exp_metric(e.target_prefixes, bf, bt, 'views');
  if b is null or a is null or b = 0 then delta := null; else delta := round((a - b) * 100.0 / b, 1); end if;
  adj := delta;
  if cardinality(e.control_prefixes) > 0 then
    cb := exp_metric(e.control_prefixes, bf, bt, e.metric);
    ca := exp_metric(e.control_prefixes, e.start_date, at, e.metric);
    if cb is not null and ca is not null and cb > 0 then
      cdelta := round((ca - cb) * 100.0 / cb, 1);
      if delta is not null then adj := delta - cdelta; end if;
    end if;
  end if;
  verdict := case when adj is null then 'inconclusive' when adj >= 20 then 'keep' when adj <= -10 then 'drop' else 'inconclusive' end;
  return jsonb_build_object('id',e.id,'name',e.name,'metric',e.metric,'window_days',win,
    'before',round(b,3),'after',round(a,3),'delta_pct',delta,'control_delta_pct',cdelta,'adjusted_pct',adj,
    'verdict',verdict,'small_sample',coalesce(bv,0) < 50);
end $$;
revoke all on function public.experiment_eval(int, date) from public, anon, authenticated;

update public.growth_experiments set control_prefixes = array['/column-'] where id in (7, 8) and control_prefixes = '{}';
