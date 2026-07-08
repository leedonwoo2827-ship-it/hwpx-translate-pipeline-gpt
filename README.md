# hwpx-translate-pipeline

> 🟢 **엔진: ChatGPT OAuth 판** — 번역/윤문을 **OpenAI Codex CLI(`codex`)** + ChatGPT 로그인으로 수행
> (API 키 불필요). *별도의 Claude(영한) 판과 구분되는, GPT 계정 할당량 기반 버전입니다.*

영문 PDF를 **한국어로 완역·윤문**하고, 원문과 유사한 구조·스타일 + 도표 삽입의 **hwpx/PDF**로
출력하는 자기완결 파이프라인. 번역/윤문은 **ChatGPT(OpenAI Codex CLI)** 로 하며 **API 키가 필요 없다**
(개인 ChatGPT 구독 할당량으로 `gpt-5.5 / gpt-5.4 / gpt-5.4-mini` 사용).

## 빠른 시작

```bash
# 1) 최초 셋업 (파이썬 의존성 + 서체 + 양식)
setup.bat            # Windows   (macOS/Linux: ./setup.sh)

# 2) GPT 번역 준비 — 최초 1회만 (Node.js 필요)
npm i -g @openai/codex
codex login          # 브라우저에서 ChatGPT 로그인

# 3) 실행 — 리뷰 뷰어(GUI)
python run.py viewer   # http://127.0.0.1:8770
```

뷰어에서: 우상단 **⚙ 연결 상태**로 로그인 확인·모델 선택 → 장을 열고
**[GPT 번역(02)] → [GPT 윤문(03)] → [교지 저장] → [hwpx 빌드]**.
전체를 한 번에 돌릴 필요 없이 **하루 한 장**씩 PDF까지 만들 수 있다.

## 주요 명령

```bash
python run.py extract                          # PDF → 01-extract
python run.py translate <장> [--model gpt-5.4] # → 02-translate (GPT 완역)
python run.py refine    <장> [--model gpt-5.4] # → 03-refine   (GPT 윤문)
python run.py viewer                           # 리뷰 뷰어(연결상태·번역·교지 diff)
python run.py build <장>                        # 04→03→02 첫 md → 05-hwpx
python run.py pdf-batch                        # hwpx → PDF (한컴, Windows 전용)
python run.py merge                            # PDF → 06-book 한 권
```

## 문서

- [docs/pipeline.md](docs/pipeline.md) — 스테이지 흐름, 출력 구조, hwpx 생성 방식, 마크다운 규약, 프로젝트 구조
- [docs/llm-codex.md](docs/llm-codex.md) — ChatGPT(codex) 설치·로그인·모델 선택·문제 해결

> 리포 제외(`.gitignore`): 원본 PDF(`_asstest/`)·산출물(`output/`)·폰트·로컬 상태(`data/`).
> codex 인증은 `~/.codex/auth.json`(홈)에만 저장되어 리포에 포함되지 않는다.
