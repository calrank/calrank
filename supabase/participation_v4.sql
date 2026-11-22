-- 닉네임 비속어 차단: 명백한 욕설만 부분 일치로 막는다(오탐을 줄이려고 '시발점' 같은 일반 낱말은 넣지 않는다).
-- 밑줄·숫자로 끊어 쓴 우회(씨_발)도 걸리도록 밑줄과 숫자를 뺀 글자로 비교한다.
create or replace function public.nickname_blocked(p_name text) returns boolean language sql immutable set search_path to 'public' as $$
  select regexp_replace(lower(coalesce(p_name,'')), '[_0-9]', '', 'g') ~ '(씨발|씨팔|씹새|씹알|병신|븅신|좆|존나|개새끼|개새|지랄|느금|니애미|애미뒤|걸레년|창녀|한남충|김치녀|섹스|야동|fuck|shit|bitch|nigger)';
$$;

create or replace function public.set_nickname(p_name text) returns text language plpgsql security definer set search_path to 'public' as $$
declare n text := trim(coalesce(p_name,''));
begin
  if auth.uid() is null then return 'login'; end if;
  if n !~ '^[가-힣A-Za-z0-9_]{2,12}$' then return 'format'; end if;
  if lower(n) in ('admin','administrator','guest','null','anonymous') or lower(n) like '%calrank%' or n like '%칼랭크%' or n like '%운영%' or n like '%관리자%' or n like '%사무국%' or n in ('익명','게스트') or public.nickname_blocked(n) then return 'reserved'; end if;
  if exists (select 1 from public.profiles where id = auth.uid() and display_name is not null and nickname_set_at > now() - interval '7 days') then return 'too_soon'; end if;
  update public.profiles set display_name = n, nickname_set_at = now() where id = auth.uid();
  return 'ok';
exception when unique_violation then return 'taken';
end $$;
revoke all on function public.set_nickname(text), public.nickname_blocked(text) from public, anon;
grant execute on function public.set_nickname(text) to authenticated;
