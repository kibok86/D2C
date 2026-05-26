# Desert to Cape — 셋업 가이드 & 4주 운영 플랜

---

## ⚡ 5분 셋업

### Step 1 — GitHub 리포지토리 생성

```bash
# 로컬에서
cd dtc/
git init
git add .
git commit -m "🚀 Desert to Cape 초기 셋업"

# GitHub에서 새 비공개 리포 생성 후
git remote add origin https://github.com/YOUR_NAME/desert-to-cape.git
git push -u origin main
```

---

### Step 2 — 스티비 계정 & API 키 발급

1. [stibee.com](https://stibee.com) 가입 (무료)
2. **주소록** → 새 주소록 생성 → 이름: `DTC Free`
3. 주소록 ID 복사 (URL에서 확인: `/lists/12345/`)
4. **계정 설정** → **API** → API 키 발급

---

### Step 3 — GitHub Secrets 등록

리포 → Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 | 필수 |
|------------|-----|-----|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | ✅ |
| `STIBEE_API_KEY` | 스티비 API 키 | ✅ |
| `STIBEE_LIST_ID_FREE` | 스티비 주소록 ID | ✅ |
| `DTC_FROM_EMAIL` | 발신 이메일 주소 | ✅ |
| `STIBEE_LIST_ID_PRO` | 유료 주소록 ID | 나중에 |

---

### Step 4 — 첫 발행 테스트 (Dry Run)

GitHub → Actions → `🗞 주간 뉴스레터 자동 발행` → **Run workflow**
- `issue_num`: 1
- `dry_run`: true ← 발송 없이 HTML만 확인

Actions 완료 후 **Artifacts**에서 HTML 다운로드해서 확인.

---

### Step 5 — 운임 데이터 주간 입력 (5분)

매주 화요일 저녁, `data/freight_rates.json` 직접 수정:

```json
{
  "gri_notice": "MSC 7월 GRI $350/TEU 예정",
  "routes": [
    { "origin": "부산", "dest": "두바이 (UAE)",
      "fak_usd": 2480, "prev_usd": 2450,
      "transit_days": 22, "status": "우회", "via": "Cape of Good Hope" }
  ]
}
```

수정 후 `git push` → 수요일 아침 자동 발행.

---

## 📅 4주 무료 운영 플랜

### Week 1 — 론칭 (6월 첫째 주 수요일)

**발행 전 체크리스트**
```
□ GitHub Actions dry-run 확인
□ 스티비 테스트 발송 (본인 이메일)
□ freight_rates.json 첫 데이터 입력
□ LinkedIn 창간 포스팅 예약
```

**수요일 자동 실행 순서**
```
07:00 KST  GitHub Actions 시작
07:02      뉴스 RSS 수집 + AI 번역
07:05      운임지수 수집 (SCFI/WCI/FBX)
07:08      환율 수집 + 히스토리 저장
07:10      AI 코멘터리 생성 (Claude API)
07:12      HTML 렌더링
07:13      스티비 발송 →구독자 수신
```

---

### Week 2 — 검증

- 스티비 대시보드에서 오픈율 확인 (목표: 35%+)
- 오픈한 독자 3~5명에게 피드백 DM
- GitHub Actions 로그 점검 (오류 있으면 수정)

---

### Week 3 — 확산

- LinkedIn POST 05 (커뮤니티 참여형) 발행
- 콜드 DM 20건 발송 (물류 포워더 타겟)
- 스티비에서 오픈율 높은 독자 세그먼트 확인

---

### Week 4 — 유료 전환 준비

- 4주 오픈 데이터 분석
- 오픈율 50%+ 독자 → 업그레이드 이메일 발송
- 스티비 유료 주소록(`DTC Pro`) 개설
- 월 9,900원 유료 구독 오픈

---

## 🔧 주간 루틴 (화요일 10분)

```bash
# 1. 운임 데이터 업데이트 (5분)
nano data/freight_rates.json  # FAK 숫자 수정

# 2. 선사/항만 특이사항 있으면 수정 (2분)
nano data/carrier_schedule.json
nano data/port_status.json

# 3. 커밋 & 푸시 (1분) → 수요일 자동 발행
git add data/
git commit -m "📊 Week N 운임 데이터 업데이트"
git push
```

---

## 🛠 문제 해결

**Actions 실패 시**
```bash
# 로컬에서 먼저 테스트
python publish.py --issue 1 --dry-run
```

**스티비 발송 실패 시**
- Actions → 실패한 Job → 로그 확인
- 스티비 API 키 만료 여부 체크
- `STIBEE_LIST_ID_FREE` 값 재확인

**번역이 안 될 때**
- `ANTHROPIC_API_KEY` Secret 확인
- `data/translation_cache.json` 삭제 후 재실행

---

## 📊 비용 구조 (4주 무료 운영)

| 항목 | 비용 | 비고 |
|------|------|------|
| GitHub Actions | 무료 | 월 2,000분 무료 |
| 스티비 | 무료 | 구독자 1,000명까지 |
| Anthropic API | ~$2~5/월 | 번역+코멘터리 |
| 도메인 (선택) | ~₩15,000/년 | 없어도 됨 |
| **합계** | **$2~5/월** | |
