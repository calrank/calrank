-- 제휴 배너의 인기 상품(쿠팡 파트너스 오픈 API 로 매주 갱신). 쓰기는 서비스 키만, 읽기는 affiliate_cards() 로만 한다.
create table if not exists public.affiliate_products (
  banner text not null,
  product_id bigint not null,
  rank int not null,
  name text not null,
  price int,
  image text not null,
  url text not null,
  rocket boolean not null default false,
  updated_at timestamptz not null default now(),
  primary key (banner, product_id)
);
alter table public.affiliate_products enable row level security;

create or replace function public.affiliate_cards(p_banner text)
returns table(product_id bigint, name text, price int, image text, url text, rocket boolean)
language sql stable security definer set search_path = public as $$
  select product_id, name, price, image, url, rocket
  from affiliate_products
  where banner = left(coalesce(p_banner, ''), 40)
    and updated_at > now() - interval '21 days'   -- 3주 넘게 갱신이 없으면 숨기고 쿠팡 배너로 돌아간다
    and url like 'https://link.coupang.com/%'
    and image like 'https://%'
  order by rank
  limit 8;
$$;
revoke all on function public.affiliate_cards(text) from public;
grant execute on function public.affiliate_cards(text) to anon, authenticated;
