"""LLM 백엔드 — OpenAI Codex CLI(`codex`) via subprocess. API 키 불필요.

인증/할당량은 codex 가 담당(사용자가 `codex login` 1회, ChatGPT OAuth).
- codex_auth: 설치/로그인 상태·계정 이메일·로그아웃·로그인 명령
- codex_runner: 모델 목록/선택 + `codex exec` 호출(CodexClient)
- errors: 공급자 공통 예외(미설치/미로그인/할당량)
"""
