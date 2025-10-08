#!/usr/bin/env python3
"""중복 제거 스크립트"""

# design.md 파일 읽기
with open('.kiro/specs/frontend/design.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 2442라인까지만 유지 (중복 제거)
clean_lines = lines[:2442]

# 정리된 파일 저장
with open('.kiro/specs/frontend/design.md', 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)

print(f"✅ 정리 완료: {len(clean_lines)} 라인")
print(f"🗑️  제거된 라인: {len(lines) - len(clean_lines)} 라인")
