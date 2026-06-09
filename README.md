# 음률 디스코드 봇 — 세팅 가이드

## 📁 파일 구조
```
discord-bot/
├── bot.py              # 메인 실행 파일
├── config.json         # 설정 파일 (토큰, 서버 ID 등)
├── requirements.txt
├── data/               # 자동 생성 (JSON 데이터)
│   ├── profanity.json  # 비속어 기록
│   └── channel_move.json # 채널 이동 기록
└── cogs/
    ├── profanity.py    # 기능 1: 비속어 감지
    ├── channel_move.py # 기능 2: 채널 자동 이동
    └── project.py      # 기능 3: 프로젝트 채널 생성
```

---

## ① 봇 만들기 (Discord Developer Portal)

1. https://discord.com/developers/applications 접속
2. **New Application** → 이름 입력 → Create
3. 왼쪽 메뉴 **Bot** → **Add Bot**
4. **TOKEN** 복사 → `config.json`의 `"token"` 에 붙여넣기
5. 아래 권한 활성화:
   - `MESSAGE CONTENT INTENT` ✅
   - `SERVER MEMBERS INTENT` ✅
   - `PRESENCE INTENT` ✅

---

## ② 봇 서버에 초대하기

1. 왼쪽 메뉴 **OAuth2 → URL Generator**
2. Scopes: `bot`, `applications.commands` 체크
3. Bot Permissions:
   - `Manage Channels` ✅ (채널 이동/생성)
   - `Read Messages / View Channels` ✅
   - `Send Messages` ✅
   - `Embed Links` ✅
   - `Read Message History` ✅
4. 생성된 URL 접속 → 서버 선택 → 초대

---

## ③ config.json 설정

```json
{
  "token": "봇토큰여기에",
  "guild_id": 서버ID숫자,        ← 서버 우클릭 → ID 복사
  "log_channel_name": "봇-비속어-기록",
  "admin_role_name": "운영진",    ← 실제 역할명과 동일하게
  "profanity_list": ["욕설1", "욕설2"],
  "category_stage1": "진행중¹",  ← 실제 카테고리명과 동일하게
  ...
}
```

---

## ④ Python 설치 및 실행

```bash
# Python 3.10 이상 필요
python --version

# 라이브러리 설치
pip install -r requirements.txt

# 봇 실행
python bot.py
```

---

## ⑤ 디코 서버 준비사항

| 항목 | 내용 |
|------|------|
| 역할 | `운영진` 역할 생성 |
| 채널 | `봇-비속어-기록` 텍스트 채널 생성 (운영진만 볼 수 있게 권한 설정) |
| 카테고리 | `진행중¹`, `진행중²`, `진행중³`, `대기중인 마감` 생성 |

---

## ⑥ 슬래시 명령어 목록

| 명령어 | 설명 | 권한 |
|--------|------|------|
| `/create title:제목 p:프로듀서 v:참여자,들` | 프로젝트 채널 생성 | 누구나 |
| `/비속어조회` | 전체 비속어 현황 | 운영진 |
| `/비속어상세 member:@멤버` | 특정 멤버 상세 조회 | 운영진 |
| `/이니셜등록 nickname:망찐 initial:𝗠𝗭` | 이니셜 등록 | 운영진 |
| `/이니셜목록` | 이니셜 전체 조회 | 누구나 |

---

## ⑦ /create 사용 예시

```
/create title:괴수의 꽃노래 p:망찐 v:망찐,히네,이설,브룩,단미,에리카
```

→ `대기중인 마감` 카테고리에 `𝗠𝗭_괴수의 꽃노래` 채널 생성  
→ 참여자 6명에게만 접근 권한 부여  
→ 채널 내 자동으로 안내 메시지 작성

---

## ⑧ 채널 이동 타이밍

- `진행중¹` 진입 시점부터 **28일 후** → `진행중²`로 자동 이동
- `진행중²` 이동 시점부터 **14일 후** → `진행중³`으로 자동 이동
- 봇 실행 중 **10분마다** 자동 체크

> 💡 채널을 수동으로 `진행중¹`로 옮겨도 자동으로 등록됩니다.
