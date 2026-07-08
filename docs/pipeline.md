# 파이프라인 상세

영문 PDF → 한국어 완역/윤문 → 원문 유사 구조·스타일의 **hwpx/PDF** 로 만드는 자기완결 파이프라인.
GPT 연동(번역/윤문) 세부는 [llm-codex.md](llm-codex.md) 참고.

## 스테이지 흐름

```
_asstest/<원본>.pdf                     원문(읽기 전용, gitignore)
   │  python run.py extract
   ▼
01-extract/<장>/  content.en.md + figures/*.png + meta.json
   │  python run.py translate <장>     (GPT/codex 완역 + 내부용 분석)
   ▼
02-translate/<장>/ content.ko.md
   │  python run.py refine <장>        (GPT/codex 윤문 — 자연스러운 한국어)
   ▼
03-refine/<장>/    content.ko.md
   │  python run.py viewer  →  좌 영문 / 우 한국어 편집·프리뷰·교지 diff → 확정
   ▼
04-review/<장>/    content.reviewed.md
   │  python run.py build <장>          (04→03→02 중 첫 md → hwpx)
   ▼
05-hwpx/<장>.hwpx
   │  python run.py pdf-batch (한컴) → merge (PyMuPDF)
   ▼
06-book/           병합 PDF 한 권
```

번역(02)·윤문(03)은 뷰어의 **[GPT 번역]/[GPT 윤문]** 버튼으로도 실행할 수 있다.
전체를 한 번에 돌릴 필요 없이 **장 하나만** 번역→윤문→저장→빌드→PDF 로 그날치만 만들 수 있다.

## 출력 구조 (책 · 교지 · 스테이지)

```
output/<책명>/<YYMMDDHHMM-라벨=교지>/
    01-extract 02-translate 03-refine 04-review 05-hwpx 06-book
```

한 실행 회차(런)가 하나의 **교지**(1교지·2교지…). 뷰어 첫 화면에서 **책**과 **교지**를 골라
장별 교정 현황을 보고, 편집 화면에서 임의 두 교지(예: 1교지 vs 최종 교지)를 라인 diff로 대비한다.
대부분 명령은 `--run <런>` / `--book <책>` 을 받으며, 생략 시 최신 런을 쓴다. 스테이지는 독립적이라
md 파일부터 시작해도 된다.

## hwpx 생성 방식

문서공방(오디세이 문서공방)의 **clone-and-refill** 방식을 이 폴더로 포팅(`pipeline/hwpx/`, lxml 전용).
`assets/hwpx_template.hwpx`(회사양식)의 명명 스타일(제목 1·2·3 / 본문 / 동그라미 / 마이너스 / 강조 /
인용 …)을 상속하고, 본문을 마지막 섹션에만 주입해 표지·머리말·로고를 보존한다. **도표(PNG) BinData
삽입은 신규 구현**(`pipeline/hwpx/images.py`).

- **양식 정본**: `assets/hwpx_template.hwpx` — 스타일 보정(본문 첫 줄 들여쓰기 등)이 구워져 있다.
  한컴에서 직접 더 수정해도 그 서식이 그대로 반영된다. 원본 회사양식은 `hwpx_template.base.hwpx` 로 백업.
  재생성: `python run.py template`.
- **크로스플랫폼**: hwpx→PDF(`pdf`/`pdf-batch`)는 한컴오피스 자동화(win32com) 기반 **Windows 전용**.
  macOS/Linux 에선 `build`(lxml)·`viewer`·`merge`(PyMuPDF)가 동작하며, hwpx 를 한컴/뷰어에서 직접
  PDF로 내보낸 뒤 `merge` 로 병합한다.

## 마크다운 규약 (KO) — 번역/윤문 산출물이 지켜야 하는 계약

- `# 제목` = 장 제목(제목 1), `## 소제목` = 제목 2, 첫 줄 `**저자**`. 헤딩 텍스트에 마크다운 기호 금지.
- 문단 = 본문, `- ` = 동그라미(○) 1단계, `  - ` = 마이너스(−) 2단계, `> ` = 인용, `**굵게**`.
- 도표: `![캡션](figures/fig-01.png)` — **경로·파일명 절대 변경 금지**(빌드가 BinData 삽입 + 캡션 렌더).
- 장 말미 `## 분석 (내부 검토용)` 섹션(요약/핵심 논점/시사점)은 편집팀이 덧붙인 내부용.

프롬프트 계약 원문: `skills/translate-ko/SKILL.md`, `skills/refine-ko/SKILL.md`(= 시스템 프롬프트).

## 리포에 포함되지 않는 것 (`.gitignore`)

- 원본 책 PDF(`_asstest/`, 저작권·대용량), 생성 산출물(`output/`), KoPub World 폰트(설치 스크립트로 대체).
- 로컬 상태 `data/codex_model.json`(선택 모델). codex 인증은 `~/.codex/auth.json`(홈)에만 저장.
- 실행하려면 원문 PDF를 `_asstest/` 에 두세요. 양식(`assets/hwpx_template.hwpx`)은 포함(로고 투명 처리).

## 프로젝트 구조

```
pipeline/  paths.py  extract.py  translate.py  build.py  merge_pdf.py  make_template.py
           setup_fonts.py  hancom_pdf.py  hancom_pdf_batch.py
           hwpx/{hwpx_gen,mdblocks,md_gen,images}.py   ← 포팅 + 신규(도표 삽입)
           llm/{codex_auth,codex_runner,errors}.py     ← codex(ChatGPT OAuth) 연동
viewer/    server.py  index.html  app.js  style.css     ← 프레임워크 無(연결상태·GPT 번역 UI 포함)
skills/    refine-ko/  translate-ko/  README.md         ← 교정·번역 프롬프트 계약(=시스템 프롬프트)
docs/      pipeline.md  llm-codex.md                     ← 파이프라인 · GPT 로그인/모델
assets/    hwpx_template.hwpx (양식 정본)  hwpx_template.base.hwpx (원본)
setup.bat run.bat  setup.sh run.sh                      ← Windows / macOS·Linux
output/    <책명>/<교지>/{01-extract 02-translate 03-refine 04-review 05-hwpx 06-book}
```
