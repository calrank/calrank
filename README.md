# calrank — 국내 동호인 스포츠대회 통합 캘린더 · 랭킹

마라톤·자전거·트레일러닝·철인3종 등 국내 동호인 스포츠 대회 정보를 여러 소스에서 자동으로 수집해 한 곳에서 보여주는 정적 사이트입니다. Vercel에 배포되어 있으며 (`calrank.vercel.app`), GitHub Actions가 주기적으로 크롤링·데이터 갱신을 담당합니다.

## 배포

GitHub `main` 브랜치에 push하면 Vercel이 자동 배포합니다. 별도 빌드 과정 없이 정적 파일을 그대로 서빙합니다.

## 로컬에서 확인하기

```bash
python3 -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```

## 주요 페이지

| 페이지 | 설명 |
|---|---|
| `index.html` | 전종목 대회 캘린더 (종목/월/지역/접수상태/거리 필터) |
| `ranking.html` | 종목·거리별 완주 기록 랭킹 (공식기록 + 사용자 입력 기록) |
| `news.html` | 종목별 뉴스 자동 수집 |
| `myrank.html` | 로그인 후 개인 기록 관리, 기록 공유 카드 생성 |
| `level.html` | 마라톤 페이스 등급 계산기 |
| `event.html?id=` | 대회별 상세 permalink 페이지 (SEO용 개별 URL, Schema.org SportsEvent, 찜하기·참가 후기) |
| `submit-event.html` | 로그인 사용자가 새 대회 정보를 제보하는 폼 (검토 후 반영) |
| `monthly.html` / `trail-monthly.html` / `cycling-monthly.html` / `triathlon-monthly.html` / `aquathlon.html` | 종목별 월간/키워드 SEO 랜딩 페이지 |
| `terms.html` / `privacy.html` / `contact.html` | 이용약관 / 개인정보처리방침 / 제휴문의 |

## 데이터 파이프라인 (GitHub Actions)

`.github/workflows/`에 정의된 3개의 자동화 워크플로우가 주기적으로 실행됩니다.

### 1. `update-events.yml` → `scripts/fetch_events.py`
대회 일정을 여러 소스에서 수집해 `events.json`에 저장합니다.

현재 소스: roadrun.co.kr, cyclo.kr, runningwikii.com, triathlon.or.kr, runningmap.kr, runneron.com

- 각 크롤러 함수(`fetch_roadrun`, `fetch_cyclo` 등)는 상호 독립적이며, 하나가 실패해도 나머지는 계속 수집됩니다.
- `merge_and_dedupe()`가 이름+날짜 기준으로 중복을 제거하고, 더 이상 소스에서 나타나지 않는 오래된 게시물(철인3종 비대회 공지, 소스가 중단된 종목)을 자동 정리합니다.
- 저장과 동시에 `generate_event_sitemap()`이 `sitemap-events.xml`을 자동 재생성합니다 (오늘 이후 대회만 포함, `event.html?id=` URL 목록).
- **소스 추가 전 체크리스트**: robots.txt 확인 (특히 AI 크롤러 차단 여부 — 발견 시 사용하지 않음), 대회 "일정 정보"만 수집(참가자 개인 기록은 수집하지 않음).
- 과거 제외 이력: `hyroxsouthkorea.com`(robots.txt에서 anthropic-ai 등 AI 크롤러 명시적 차단, 2026-08-27 제외)

### 2. `update-news.yml` → `scripts/fetch_news.py`
종목별 공식 협회 뉴스를 수집해 `news.json`에 저장합니다.

### 3. `update-official-records.yml` → `scripts/fetch_official_records.py`
제주MBC 국제평화마라톤 등 대회 주최측이 공식 발표한 완주 기록을 Supabase `official_records` 테이블에 저장합니다. `SUPABASE_SERVICE_ROLE_KEY`가 GitHub Secret으로 등록되어 있어야 동작합니다 (RLS로 anon 키는 쓰기 불가).

## 백엔드 (Supabase)

- `profiles`, `personal_records`: 로그인 사용자의 개인 대회 기록. RLS로 본인만 조회/수정/삭제 가능.
- `official_records`: 대회 주최측 공식 기록. RLS로 조회는 공개, 쓰기는 `service_role` 키(GitHub Actions)만 가능. `claimed_by_user_id` 컬럼으로 사용자가 본인 기록을 클레임할 수 있음 (트리거로 기록 데이터 자체는 변조 불가).
- `get_top_rankings()` RPC 함수가 `personal_records` + `official_records`를 UNION으로 합쳐 랭킹을 계산하고, 개인 기록은 이름을 마스킹 처리합니다.
- `event_saves`: 로그인 사용자의 대회 찜하기(즐겨찾기). `get_save_count()`, `get_top_saved_events()` RPC로 집계.
- `event_reviews`: 대회별 참가 후기(별점 1~5 + 텍스트). 조회는 공개, 작성/수정/삭제는 본인만. `get_review_summary()` RPC로 평균 별점 집계.
- `event_submissions`: 사용자가 제보한 신규 대회 정보. 반영 여부는 Kevin님이 Supabase Table Editor에서 직접 검토.

## SEO

- `robots.txt` / `sitemap.xml`(주요 페이지) / `sitemap-events.xml`(대회별 상세 페이지, 크롤링마다 자동 갱신) 모두 구글·네이버 서치콘솔에 등록되어 있습니다.
- 각 페이지에 OG/Twitter 메타태그, `event.html`에는 대회별 `SportsEvent` Schema.org JSON-LD가 삽입됩니다.
- Vercel Web Analytics가 전 페이지에 설치되어 있습니다 (`/_vercel/insights/script.js`).

## 다음 단계 후보

- 대회별 거리 데이터 정규화 (현재 소수의 "거리 미확인" 케이스 존재, 특히 runningmap.kr 소스)
- 백링크 확보 (네이버 지식iN, 러닝 커뮤니티 등)
- 개인 기록(personal_records) 실사용자 데이터 축적
