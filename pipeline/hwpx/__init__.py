"""문서공방에서 포팅한 자기완결 HWPX 생성 엔진 (lxml only).

- hwpx_gen: clone-and-refill (회사 템플릿 스타일 재사용, 마지막 섹션에 본문 주입)
- mdblocks: Markdown → typed block 파서
- md_gen:   payload → Markdown (문자열은 그대로 통과)
- images:   (신규) BinData 도표 삽입
"""
