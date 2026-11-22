-- 참여 기능 8차: 대회 현장 확인(다녀온 사람이 급수·화장실·교통 등을 확인) + 대회 후기에 닉네임 표시. 2026-11-22
-- 원칙: 다녀온 사람이 닉네임으로 남기고, 다른 사람이 같은 항목을 확인한다. 로그인·닉네임이 있어야 올릴 수 있다.
create table if not exists public.event_aspects (
  event_id text not null check (char_length(event_id) between 3 and 120 and event_id !~ '[[:cntrl:]]'),
  aspect text not null check (aspect in ('water','toilet','access','start','marks','bag')),
  user_id uuid not null references auth.users(id) on delete cascade,
  answer text not null check (answer in ('good','bad')),
  note text check (note is null or char_length(note) <= 40),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (event_id, aspect, user_id)
);
alter table public.event_aspects enable row level security;
revoke all on table public.event_aspects from anon, authenticated;
create index if not exists event_aspects_user on public.event_aspects (user_id, updated_at desc);

-- 올리기. 반환: login | nick | bad | slow | ok
create or replace function public.submit_event_aspect(p_event text, p_aspect text, p_answer text, p_note text default null) returns text language plpgsql security definer set search_path to 'public' as $$
declare uid uuid := auth.uid(); n text := nullif(trim(regexp_replace(coalesce(p_note,''), '[[:cntrl:]]', ' ', 'g')), '');
begin
  if uid is null then return 'login'; end if;
  if p_event is null or char_length(p_event) not between 3 and 120 or p_event ~ '[[:cntrl:]]' or p_aspect not in ('water','toilet','access','start','marks','bag') or p_answer not in ('good','bad') then return 'bad'; end if;
  if n is not null and (char_length(n) > 40 or public.nickname_blocked(n) or n ~* '(https?://|www\.|[a-z0-9.-]+\.(com|net|kr|io|me)\b|[0-9]{2,4}-[0-9]{3,4}-[0-9]{4}|@)') then return 'bad'; end if;
  if not exists (select 1 from public.profiles where id = uid and display_name is not null) then return 'nick'; end if;
  if (select count(*) from public.event_aspects where user_id = uid and updated_at > now() - interval '1 hour') >= 30 then return 'slow'; end if;
  insert into public.event_aspects (event_id, aspect, user_id, answer, note) values (p_event, p_aspect, uid, p_answer, n)
  on conflict (event_id, aspect, user_id) do update set answer = excluded.answer, note = excluded.note, updated_at = now();
  return 'ok';
end $$;

-- 항목별 집계: 좋았어요/아쉬웠어요 수(서로 다른 로그인 사용자), 마지막 확인일, 처음 확인한 닉네임(신고 3명 이상이면 가림), 내 답
create or replace function public.event_aspect_summary(p_event text) returns table(aspect text, good_n int, bad_n int, last_at timestamptz, first_name text, mine text) language sql stable security definer set search_path to 'public' as $$
  select a.aspect,
    (count(*) filter (where a.answer = 'good'))::int,
    (count(*) filter (where a.answer = 'bad'))::int,
    max(a.updated_at),
    (select p.display_name from public.event_aspects f join public.profiles p on p.id = f.user_id
      where f.event_id = a.event_id and f.aspect = a.aspect and p.display_name is not null
        and not exists (select 1 from public.nickname_reports r where r.target = f.user_id group by r.target having count(distinct r.reporter) >= 3)
      order by f.created_at limit 1),
    (max(a.answer) filter (where a.user_id = auth.uid()))
  from public.event_aspects a where a.event_id = p_event group by a.event_id, a.aspect;
$$;

-- 내 현장 확인(삭제용)
create or replace function public.my_event_aspects() returns table(event_id text, aspect text, answer text, note text, updated_at timestamptz) language sql stable security definer set search_path to 'public' as $$
  select event_id, aspect, answer, note, updated_at from public.event_aspects where user_id = auth.uid() order by updated_at desc limit 100;
$$;

create or replace function public.delete_event_aspect(p_event text, p_aspect text) returns text language plpgsql security definer set search_path to 'public' as $$
declare uid uuid := auth.uid();
begin
  if uid is null then return 'login'; end if;
  delete from public.event_aspects where event_id = p_event and aspect = p_aspect and user_id = uid;
  if not found then return 'none'; end if;
  return 'ok';
end $$;

-- 대회 후기 목록(닉네임 포함). 로그인해서 쓴 후기에만 닉네임이 붙고, 신고 3명 이상이면 가린다. 본인 후기 표시(mine)와 삭제를 위해 id도 준다.
create or replace function public.event_review_list(p_event text) returns table(id bigint, rating smallint, comment text, created_at timestamptz, nick text, mine boolean) language sql stable security definer set search_path to 'public' as $$
  select r.id, r.rating, r.comment, r.created_at,
    (select p.display_name from public.profiles p where p.id = r.user_id
       and not exists (select 1 from public.nickname_reports x where x.target = r.user_id group by x.target having count(distinct x.reporter) >= 3)),
    (r.user_id is not null and r.user_id = auth.uid())
  from public.event_reviews r where r.event_id = p_event order by r.created_at desc limit 20;
$$;

revoke all on function public.submit_event_aspect(text, text, text, text), public.event_aspect_summary(text), public.my_event_aspects(), public.delete_event_aspect(text, text), public.event_review_list(text) from public, anon, authenticated;
grant execute on function public.event_aspect_summary(text), public.event_review_list(text) to anon, authenticated;
grant execute on function public.submit_event_aspect(text, text, text, text), public.my_event_aspects(), public.delete_event_aspect(text, text) to authenticated;
