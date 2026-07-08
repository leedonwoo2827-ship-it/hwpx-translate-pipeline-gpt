# UNIVERSITIES AFTER AI — 한국어 내부 연구물 파이프라인

영문 학술 에세이집 *「UNIVERSITIES AFTER AI: Voices from the Global Frontier」*(IAUP /
Almaty Management University / Global Education Futures, 2026, 192p)를 **한국어 완역 +
내부용 요약·시사점 분석**으로 만들고, **원문과 유사한 구조·스타일 + 도표 삽입**의 **hwpx**로
출력하는 자기완결 파이프라인.

## 파이프라인 (output 스테이지 폴더)

```
_asstest/UNIVERSITIES AFTER AI.pdf   원문(읽기 전용)
        │  python run.py extract
        ▼
output/01-extract/<장>/   content.en.md  +  figures/*.png  +  meta.json
        │  번역·분석 (GPT: OpenAI Codex CLI, ChatGPT OAuth 할당량 — API 키 불필요)
        ▼
output/02-translate/<장>/ content.ko.md          ← GPT 완역, 사람이 편집
        │  python run.py viewer  →  좌 영문 / 우 한국어 편집 + 프리뷰 + 도표
        ▼
output/03-review/<장>/    content.reviewed.md    ← 사람이 확정
        │  python run.py build <장>
        ▼
output/04-hwpx/<장>/      <장>.hwpx              ← 최종(구조·스타일 미러 + 도표)
```

## hwpx 생성 방식

문서공방(오디세이 문서공방)의 **clone-and-refill** 방식을 이 폴더로 포팅
(`pipeline/hwpx/`, lxml 전용). `assets/hwpx_template.hwpx`(회사양식) 의 명명 스타일
(제목 1·2·3 / 본문 / 동그라미 / 마이너스 / 강조 / 인용 …)을 상속하고, 본문을 마지막
섹션에만 주입해 표지·머리말·로고를 보존한다. **도표(PNG) BinData 삽입은 신규 구현**
(`pipeline/hwpx/images.py`).

- **양식 정본**: `assets/hwpx_template.hwpx` — 스타일 보정(본문 첫 줄 들여쓰기 등)이
  구워져 있다. 한컴에서 직접 더 수정해도 되며 그 서식이 그대로 반영된다.
  원본 회사양식은 `assets/hwpx_template.base.hwpx` 로 백업. 재생성: `python run.py template`.

## 사용

> **리포에 포함되지 않는 것**(`.gitignore`): 원본 책 PDF(`_asstest/`, 저작권·대용량)와 생성 산출물(`output/`), KoPub World 폰트 TTF(설치 스크립트로 대체). 실행하려면 원문 PDF를 `_asstest/UNIVERSITIES AFTER AI.pdf` 에 두세요. 양식(`assets/hwpx_template.hwpx`)은 포함되며 로고 이미지는 제거(투명 처리)되어 있습니다.

**초기 셋업**(의존성 + KoPub World 서체 + 양식 정본):

```bash
setup.bat        # Windows
./setup.sh       # macOS / Linux
```

**실행**(대화형 메뉴: 뷰어 / 빌드 / PDF / 병합 / 추출):

```bash
run.bat          # Windows
./run.sh         # macOS / Linux
```

**개별 명령**(어느 OS든 동일):

```bash
python run.py extract                                     # PDF → 01-extract (새 런 생성)
python run.py translate <chapter-id> [--run] [--model]    # 01 EN → 02-translate (GPT/codex 완역)
python run.py refine    <chapter-id> [--run] [--model]    # EN+02 → 03-refine (GPT/codex 윤문)
python run.py viewer                                      # 리뷰 뷰어(연결상태·GPT 번역·초벌 vs 교정본 diff)
python run.py build <chapter-id> [--run <런>] [--book <책>]  # 04→03→02 첫 md → 05-hwpx
python run.py merge [--run <런>] [--book <책>]              # 05-hwpx/*.pdf → 06-book (PyMuPDF)
python run.py pdf-batch                                   # 05-hwpx/*.hwpx → PDF (한컴, Windows 전용)
```

> **GPT 번역/윤문 전제**: Node.js + `npm i -g @openai/codex` 설치 후 1회 `codex login`(ChatGPT OAuth).
> API 키가 필요 없으며 개인 ChatGPT 구독 할당량으로 `gpt-5.5/5.4/5.4-mini` 를 쓴다.
> 뷰어의 **⚙ 연결 상태**에서 로그인·모델선택, 편집 화면의 **[GPT 번역]/[GPT 윤문]** 버튼으로 실행.
> 자세히: [docs/llm-codex.md](docs/llm-codex.md).

> **크로스플랫폼 주의**: hwpx→PDF 변환(`pdf`/`pdf-batch`)은 한컴오피스 자동화(win32com) 기반이라 **Windows 전용**입니다. macOS/Linux 에서는 `build`(lxml)·`viewer`·`merge`(PyMuPDF) 가 모두 동작하며, hwpx 를 한컴/뷰어에서 직접 PDF로 내보낸 뒤 `merge` 로 한 권 병합하세요.

### 출력 구조 (책 · 교지 · 스테이지)

```
output/<책명>/<YYMMDDHHMM-라벨=교지>/
    01-extract 02-translate 03-refine 04-review 05-hwpx 06-book
```

한 실행 회차(런)가 하나의 **교지**(1교지·2교지…). 뷰어 첫 화면에서 **책**과 **교지**를 골라
장별 교정 현황을 보고, 편집 화면에서 임의 두 교지(예: 1교지 vs 최종 교지)를 라인 diff로 대비한다.

## 마크다운 규약 (KO)

- `# 제목` = 장 제목(제목 1), `## 소제목` = 제목 2, 첫 줄 `**저자**`
- 문단 = 본문, `- ` = 동그라미(○) 불릿, `  - ` = 마이너스(−) 2단계, `> ` = 인용, `**굵게**`
- 도표: `![캡션](figures/fig-01.png)` — 빌드 시 BinData 삽입 + 캡션(인용) 렌더
- 장 말미 `## 분석` 섹션(요약/핵심 논점/시사점)은 편집팀이 덧붙인 내부용

## 상태 / 로드맵

- **현재**: 번역(02)·윤문(03)을 **OpenAI Codex CLI(`codex`, ChatGPT OAuth 할당량)** 로 자동화.
  API 키·외부 SDK 없이 개인 ChatGPT 구독으로 `gpt-5.5/5.4/5.4-mini` 사용. Claude 비의존.
- **선택 확장**: 목록 화면 행별 빠른 번역 버튼, `##` 소제목 단위 청킹(긴 장 출력 잘림 대비).
- **선택 확장**: 포팅한 hwpx 모듈을 FastMCP 로 감싸 Claude Desktop 플러그인(MCP)화.

## 구조

```
pipeline/  paths.py  extract.py  translate.py  build.py  merge_pdf.py  make_template.py
           setup_fonts.py  hancom_pdf.py  hancom_pdf_batch.py
           hwpx/{hwpx_gen,mdblocks,md_gen,images}.py   ← 포팅 + 신규
           llm/{codex_auth,codex_runner,errors}.py     ← codex(ChatGPT OAuth) 연동
viewer/    server.py  index.html  app.js  style.css     ← 프레임워크 無(연결상태·GPT 번역 UI 포함)
skills/    refine-ko/  translate-ko/  README.md         ← 교정·번역 프롬프트 계약(=시스템 프롬프트)
docs/      llm-codex.md                                 ← GPT 로그인·모델·문제해결
assets/    hwpx_template.hwpx (양식 정본)  hwpx_template.base.hwpx (원본)
setup.bat run.bat  setup.sh run.sh                      ← Windows / macOS·Linux
output/    <책명>/<교지>/{01-extract 02-translate 03-refine 04-review 05-hwpx 06-book}
```
