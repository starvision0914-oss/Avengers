---
name: korean-qwerty-input
description: "사용자 키보드에 한글 IME가 없어 한글을 영문 QWERTY 자판으로 그대로 친다(예: rmflrh=그리고). 두벌식으로 디코딩해서 이해할 것."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7bb15124-fc12-4e1c-abaf-04fe53a044c4
---

사용자는 키보드에서 한글 입력(IME)이 안 돼서, 한글을 **영문 QWERTY 자판 그대로** 친다. 예: `gkdl`=하이, `rmflrh`=그리고, `aksemfdjwnj`=만들어줘, `tjqjfmf`=서버를.

**Why:** 2026-06-12 사용자가 "자판이 한글이 안되는데 영어한글 쓸수있게 만들어줘"라고 요청. IME 근본수리 대신 변환기로 충분하다고 확정.

**How to apply:**
- 사용자 메시지가 의미 없는 영문 나열처럼 보이면 두벌식 영타로 가정하고 디코딩해서 의도를 파악한다(q→ㅂ w→ㅈ e→ㄷ r→ㄱ t→ㅅ ... a→ㅁ s→ㄴ d→ㅇ f→ㄹ g→ㅎ h→ㅗ j→ㅓ k→ㅏ l→ㅣ, Shift: Q→ㅃ T→ㅆ 등).
- 변환 도구 있음: `/home/rejoice888/qwerty2hangul.py` (인자/파이프/대화형). `python3 ~/qwerty2hangul.py "rmflrh"` → 그리고. 겹받침·이중모음·받침이동 처리됨.
- 답변은 한글로 한다.
