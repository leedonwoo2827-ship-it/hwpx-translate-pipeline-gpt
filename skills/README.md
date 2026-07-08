# skills/ — AI 단계 프롬프트 모음

파이프라인 단계 중 **프롬프트로 구동되는(=현재 Claude, 향후 로컬 LLM) 단계**의 지침을
모아 둔다. 결정론적 단계(추출·빌드·병합·서체 설치)는 코드/CLI이며 루트 `README.md` 참조.

| 스킬 | 파이프라인 단계 | 입력 → 출력 | 설명 |
|------|----------------|-------------|------|
| [translate-ko](translate-ko/SKILL.md) | 02-translate | EN md → KO md(+분석) | 영문 원문을 한국어로 완역 + 내부용 분석 섹션 |
| [refine-ko](refine-ko/SKILL.md) | 03-refine | EN md + 02 KO md → KO md | 직역투 윤문(자연스러움 교정), 의미·포맷 보존 |

공통 계약:
- 대상 문서 = 문서공방 hwpx 마크다운 규약(제목/본문/불릿/인용/도표 링크). 포맷 훼손 금지.
- 출력은 런 폴더의 해당 스테이지 `content.ko.md`.
- 검토는 로컬 웹 뷰어(`run.py viewer`): 좌 영문 / 우 편집 + 초벌 대비 diff → 04-review 저장.
- 로컬 LLM 이관 시 각 SKILL.md를 시스템 프롬프트로 사용, 장 단위 처리 + diff 회귀 점검.
