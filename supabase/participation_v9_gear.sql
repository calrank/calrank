-- 참여 기능 9차: 기어 "써 봤어요"(장비를 써 본 사람이 효과를 확인하고 닉네임이 남는다). 2026-11-22
create table if not exists public.gear_uses (
  gear_id text not null check (gear_id ~ '^gear-[a-z0-9-]{1,80}$'),
  user_id uuid not null references auth.users(id) on delete cascade,
  answer text not null check (answer in ('good','bad')),
  period smallint check (period is null or period between 1 and 3),  -- 1: 한 달 미만, 2: 1~6개월, 3: 6개월 이상
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (gear_id, user_id)
);
alter table public.gear_uses enable row level security;
revoke all on table public.gear_uses from anon, authenticated;
create index if not exists gear_uses_user on public.gear_uses (user_id, updated_at desc);

-- 반환: login | nick | bad | slow | ok
create or replace function public.submit_gear_use(p_gear text, p_answer text, p_period int default null) returns text language plpgsql security definer set search_path to 'public' as $$
declare uid uuid := auth.uid();
begin
  if uid is null then return 'login'; end if;
  if p_gear is null or p_gear !~ '^gear-[a-z0-9-]{1,80}$' or p_answer not in ('good','bad') or (p_period is not null and p_period not between 1 and 3) then return 'bad'; end if;
  if not exists (select 1 from public.profiles where id = uid and display_name is not null) then return 'nick'; end if;
  if (select count(*) from public.gear_uses where user_id = uid and updated_at > now() - interval '1 hour') >= 30 then return 'slow'; end if;
  insert into public.gear_uses (gear_id, user_id, answer, period) values (p_gear, uid, p_answer, p_period)
  on conflict (gear_id, user_id) do update set answer = excluded.answer, period = excluded.period, updated_at = now();
  return 'ok';
end $$;

-- 집계: 효과 있었어요/별로였어요 수, 6개월 이상 쓴 사람 수, 마지막 확인일, 처음 남긴 닉네임(신고 3명 이상이면 가림), 내 답
create or replace function public.gear_use_summary(p_gear text) returns table(good_n int, bad_n int, long_n int, last_at timestamptz, first_name text, mine text, my_period smallint) language sql stable security definer set search_path to 'public' as $$
  select (count(*) filter (where g.answer = 'good'))::int, (count(*) filter (where g.answer = 'bad'))::int,
    (count(*) filter (where g.period = 3))::int, max(g.updated_at),
    (select p.display_name from public.gear_uses f join public.profiles p on p.id = f.user_id
      where f.gear_id = p_gear and p.display_name is not null
        and not exists (select 1 from public.nickname_reports r where r.target = f.user_id group by r.target having count(distinct r.reporter) >= 3)
      order by f.created_at limit 1),
    (max(g.answer) filter (where g.user_id = auth.uid())),
    (max(g.period) filter (where g.user_id = auth.uid()))
  from public.gear_uses g where g.gear_id = p_gear;
$$;

create or replace function public.my_gear_uses() returns table(gear_id text, answer text, period smallint, updated_at timestamptz) language sql stable security definer set search_path to 'public' as $$
  select gear_id, answer, period, updated_at from public.gear_uses where user_id = auth.uid() order by updated_at desc limit 100;
$$;

create or replace function public.delete_gear_use(p_gear text) returns text language plpgsql security definer set search_path to 'public' as $$
declare uid uuid := auth.uid();
begin
  if uid is null then return 'login'; end if;
  delete from public.gear_uses where gear_id = p_gear and user_id = uid;
  if not found then return 'none'; end if;
  return 'ok';
end $$;

revoke all on function public.submit_gear_use(text, text, int), public.gear_use_summary(text), public.my_gear_uses(), public.delete_gear_use(text) from public, anon, authenticated;
grant execute on function public.gear_use_summary(text) to anon, authenticated;
grant execute on function public.submit_gear_use(text, text, int), public.my_gear_uses(), public.delete_gear_use(text) to authenticated;
