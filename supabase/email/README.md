# Supabase 인증 메일 템플릿 (한국어)

Supabase 대시보드 → Authentication → Emails → Templates 에 붙여 넣는다.
**calrank.kr/auth-confirm.html 이 배포된 뒤에** 적용한다(먼저 적용하면 링크가 404).

| 템플릿 | 제목(Subject) | 파일 |
|---|---|---|
| Confirm sign up | [칼랭크] 이메일 인증을 완료해 주세요 | confirm.html |
| Reset password | [칼랭크] 비밀번호 재설정 링크 | recovery.html |
| Change email address | [칼랭크] 이메일 변경을 확인해 주세요 | email_change.html |

- 링크는 보낸 도메인(mail.calrank.kr)과 같은 계열인 calrank.kr 로 연결한다. 받는 쪽 스팸 검사에서 유리하다.
- 이미지·추적 링크 없이 글자만 쓴다(Resend 의 열람·클릭 추적도 끈 상태).
- 모든 메일에 "스팸함에 있다면 스팸 해제를 눌러 달라"는 안내가 들어 있다.
- Magic Link / Invite 는 쓰지 않는다(로그인은 이메일+비밀번호, 소셜).
