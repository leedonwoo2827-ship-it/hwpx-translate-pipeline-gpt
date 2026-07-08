# GPT 번역/윤문 — OpenAI Codex CLI(ChatGPT OAuth) 연동

번역(02-translate)·윤문(03-refine) 단계를 **OpenAI Codex CLI(`codex`)** 로 자동화한다.
`codex` 에 **ChatGPT 계정으로 1회 로그인**하면, 그 계정의 구독 할당량으로 GPT 모델
(`gpt-5.5` / `gpt-5.4` / `gpt-5.4-mini`)을 쓴다. **API 키가 필요 없다.**

## 왜 이 방식인가
- API 키 발급/과금 설정 없이 개인 ChatGPT 구독 할당량으로 바로 사용.
- `codex exec` 는 공식 비대화식 실행 모드 — 서버가 프롬프트를 stdin 으로 넘기고 결과만 받는다.
- 토큰 저장·갱신은 전적으로 `codex` 가 담당(`~/.codex/auth.json` 또는 OS 키링). 앱은 상태만 읽는다.

## 설치 (1회)
1. **Node.js** 설치 (https://nodejs.org).
2. codex 설치:
   ```
   npm i -g @openai/codex
   ```
3. ChatGPT 로그인(브라우저 OAuth):
   ```
   codex login
   ```
   - 뷰어(GUI)에서 **⚙ 연결 상태 → 🖥️ 로그인 관리** 버튼을 눌러도 새 터미널에서 `codex login` 이 열린다.
4. 상태 확인:
   ```
   codex login status      # exit 0 이면 로그인됨
   codex debug models      # 사용 가능한 모델 목록(JSON)
   ```

## 사용
### 뷰어(GUI) — 권장, 장 단위 온디맨드
```
python run.py viewer      # http://127.0.0.1:8770
```
- 상단 **⚙ 연결 상태**: 연결 여부·계정 이메일 확인, **사용 모델** 선택 후 **적용**.
- 장을 열고 **[GPT 번역(02)]** → 초벌 완역이 우측 편집창에 채워짐 → 검토 → **[교지 저장]**.
- **[GPT 윤문(03)]** → 초벌(02)을 자연스럽게 다듬은 교정본 → **[대비 보기]** 로 변경점 확인.
- 확정 후 **[hwpx 빌드]**, 이어서 `python run.py pdf <hwpx>` 로 PDF.

### CLI
```
python run.py translate <chapter-id> [--run <런>] [--model gpt-5.4]
python run.py refine    <chapter-id> [--run <런>] [--model gpt-5.4]
```
- 시스템 프롬프트 = `skills/translate-ko/SKILL.md` · `skills/refine-ko/SKILL.md` 본문(그대로).
- 입출력: `01-extract/<장>/content.en.md` → `02-translate/…/content.ko.md` → `03-refine/…/content.ko.md`.
- 도표 라인 `![캡션](figures/fig-0N.png)` 은 경로/파일명 그대로 보존해야 한다(빌드가 BinData 삽입).
  산출물에서 경로가 누락/변형되면 콘솔에 경고를 출력한다.

## 모델 선택 저장
- 선택 모델은 `data/codex_model.json`(로컬, gitignore) 에 저장된다. 비어 있으면 codex 가 자동 선택.
- 환경변수로도 지정 가능: `CODEX_MODEL=gpt-5.4`, 호출 타임아웃 `CODEX_EXEC_TIMEOUT=600`(초).

## 문제 해결
| 증상 | 원인/해결 |
|---|---|
| `codex 미설치` 칩(빨강) | Node.js + `npm i -g @openai/codex`. PATH 등록 확인(`where codex`). |
| `미로그인` 칩(빨강) | `codex login` (또는 GUI 로그인 관리). 완료 후 **새로고침**. |
| 번역 중 `할당량 초과` | ChatGPT 계정 사용 한도 초과. 잠시 후 재시도 또는 상위 구독(Plus/Pro). |
| 응답 시간 초과 | 긴 장은 `CODEX_EXEC_TIMEOUT` 를 늘린다(예: 600). |
| 결과가 비었다/이상 | `codex debug models` 로 모델 가용성 확인, 모델을 바꿔 재시도. |

## 하루 필요분량만
전체를 한 번에 돌릴 필요 없다. 장 하나만 **번역 → 윤문 → 저장 → hwpx 빌드 → PDF** 로 그날치만
만들 수 있다. 사용량은 ChatGPT 구독 할당량 안에서 소비된다(별도 일일 카운터 없음).
