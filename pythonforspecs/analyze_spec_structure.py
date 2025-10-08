#!/usr/bin/env python3
"""Spec 문서 구조 분석 도구 - 라인 번호 추적 기능 포함"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SectionMatch:
    """섹션 매칭 정보"""
    title: str
    line_number: int
    match_type: str  # 'exact', 'partial', 'similar'
    similarity: float  # 0.0 ~ 1.0


class SpecAnalyzer:
    """Spec 문서 분석기 - 라인 번호 추적"""
    
    REQ_SECTIONS = {
        "Introduction": 14.3,
        "User Stories": 14.3,
        "Acceptance Criteria": 14.3,
        "Functional Requirements": 14.3,
        "Non-Functional Requirements": 14.3,
        "Dependencies": 14.3,
        "Constraints": 14.3
    }
    
    DESIGN_SECTIONS = {
        "critical": {
            "Overview": 5,
            "Shared Library Integration": 5,
            "Architecture": 5,
            "Components and Interfaces": 5,
            "Error Handling": 5,
            "Production Considerations": 5,
            "Data Models": 5,
            "Service Integration": 5
        },
        "high": {
            "Integration Testing Strategy": 3,
            "Performance Benchmarks": 3,
            "Monitoring": 3,
            "API Specification": 3,
            "Database Schema": 3,
            "Configuration Management": 3,
            "Logging Strategy": 3
        },
        "medium": {
            "Observability": 2,
            "Disaster Recovery": 2,
            "Compliance and Audit": 2,
            "Dependency Management": 2,
            "Development Workflow": 2,
            "Capacity Planning": 2
        },
        "low": {
            "Documentation": 1,
            "Internationalization": 1,
            "Accessibility": 1,
            "Versioning Strategy": 1,
            "Cost Optimization": 1,
            "Team Collaboration": 1
        }
    }
    
    def __init__(self, spec_path: str):
        self.spec_path = Path(spec_path)
    
    def analyze_spec(self):
        """전체 Spec 분석"""
        print(f"\n{'='*80}")
        print(f"📋 Spec 분석: {self.spec_path.name}")
        print(f"{'='*80}\n")
        
        req_result = self._analyze_requirements()
        design_result = self._analyze_design()
        tasks_result = self._analyze_tasks()
        
        overall = (req_result["score"] * 0.3 + 
                  design_result["score"] * 0.5 + 
                  tasks_result["score"] * 0.2)
        
        print(f"\n{'='*80}")
        print(f"📊 전체 점수: {overall:.1f}%")
        print(f"  - Requirements: {req_result['score']:.1f}%")
        print(f"  - Design: {design_result['score']:.1f}%")
        print(f"  - Tasks: {tasks_result['score']:.1f}%")
        print(f"{'='*80}\n")
        
        return {
            "spec_name": self.spec_path.name,
            "overall_score": round(overall, 1),
            "requirements": req_result,
            "design": design_result,
            "tasks": tasks_result
        }
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """두 문자열의 유사도 계산 (0.0 ~ 1.0)"""
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        # 완전 일치
        if str1_lower == str2_lower:
            return 1.0
        
        # 부분 문자열 포함
        if str1_lower in str2_lower or str2_lower in str1_lower:
            return 0.8
        
        # 단어 기반 매칭
        words1 = set(str1_lower.split())
        words2 = set(str2_lower.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _find_section_matches(
        self, 
        required_section: str, 
        sections: List[Tuple[str, int]]
    ) -> List[SectionMatch]:
        """섹션 매칭 찾기 (라인 번호 포함)"""
        matches = []
        
        for section_title, line_num in sections:
            similarity = self._calculate_similarity(required_section, section_title)
            
            if similarity >= 1.0:
                match_type = 'exact'
            elif similarity >= 0.8:
                match_type = 'partial'
            elif similarity >= 0.5:
                match_type = 'similar'
            else:
                continue
            
            matches.append(SectionMatch(
                title=section_title,
                line_number=line_num,
                match_type=match_type,
                similarity=similarity
            ))
        
        # 유사도 순으로 정렬
        matches.sort(key=lambda x: x.similarity, reverse=True)
        return matches

    
    def _analyze_requirements(self) -> Dict:
        """Requirements.md 분석 - 라인 번호 추적"""
        file_path = self.spec_path / "requirements.md"
        
        print(f"📝 Requirements.md")
        print(f"{'─'*80}")
        
        if not file_path.exists():
            print(f"❌ 파일 없음\n")
            return {"score": 0, "found": {}, "missing": list(self.REQ_SECTIONS.keys()), "similar": {}}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 섹션 추출 (라인 번호 포함)
        sections = []
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('##') and not line.strip().startswith('###'):
                title = line.strip().lstrip('#').strip()
                sections.append((title, i))
        
        found = {}
        missing = []
        similar = {}
        
        for req_section in self.REQ_SECTIONS.keys():
            matches = self._find_section_matches(req_section, sections)
            
            if matches and matches[0].match_type in ['exact', 'partial']:
                # 정확한 매칭 또는 부분 매칭
                found[req_section] = matches[0]
            else:
                missing.append(req_section)
                # 유사한 섹션이 있으면 기록
                if matches:
                    similar[req_section] = matches[:3]  # 상위 3개
        
        score = (len(found) / len(self.REQ_SECTIONS)) * 100
        
        print(f"총 라인 수: {len(lines):,}")
        print(f"점수: {score:.1f}%")
        
        if found:
            print(f"\n✅ 발견된 섹션 ({len(found)}개):")
            for section, match in found.items():
                icon = "✓" if match.match_type == 'exact' else "≈"
                print(f"  {icon} {section:40s} → 라인 {match.line_number:4d} ({match.title})")
        
        if missing:
            print(f"\n❌ 누락된 섹션 ({len(missing)}개):")
            for section in missing:
                print(f"  ✗ {section}")
                # 유사한 섹션 제안
                if section in similar:
                    print(f"    💡 유사 섹션:")
                    for match in similar[section]:
                        print(f"       - 라인 {match.line_number:4d}: {match.title} (유사도: {match.similarity:.0%})")
        
        print()
        return {
            "score": round(score, 1), 
            "found": found, 
            "missing": missing,
            "similar": similar
        }

    
    def _analyze_design(self) -> Dict:
        """Design.md 분석 - 라인 번호 추적"""
        file_path = self.spec_path / "design.md"
        
        print(f"🏗️  Design.md")
        print(f"{'─'*80}")
        
        if not file_path.exists():
            print(f"❌ 파일 없음\n")
            return {"score": 0, "found": {}, "missing": {}, "similar": {}, "priority_scores": {}}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 섹션 추출 (라인 번호 포함, 번호 제거)
        sections = []
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('##') and not line.strip().startswith('###'):
                title = line.strip().lstrip('#').strip()
                # 번호 제거 (예: "1. Overview" -> "Overview")
                title = re.sub(r'^\d+\.\s*', '', title)
                sections.append((title, i))
        
        found_by_priority = {p: {} for p in self.DESIGN_SECTIONS.keys()}
        missing_by_priority = {p: [] for p in self.DESIGN_SECTIONS.keys()}
        similar_by_priority = {p: {} for p in self.DESIGN_SECTIONS.keys()}
        
        total_weight = 0
        earned_weight = 0
        
        for priority, section_dict in self.DESIGN_SECTIONS.items():
            for section_name, weight in section_dict.items():
                total_weight += weight
                
                matches = self._find_section_matches(section_name, sections)
                
                if matches and matches[0].match_type in ['exact', 'partial']:
                    found_by_priority[priority][section_name] = matches[0]
                    earned_weight += weight
                else:
                    missing_by_priority[priority].append(section_name)
                    if matches:
                        similar_by_priority[priority][section_name] = matches[:3]
        
        score = (earned_weight / total_weight) * 100 if total_weight > 0 else 0
        
        # 우선순위별 점수
        priority_scores = {}
        for priority, section_dict in self.DESIGN_SECTIONS.items():
            total = sum(section_dict.values())
            earned = sum(section_dict[s] for s in found_by_priority[priority].keys())
            priority_scores[priority] = round((earned / total) * 100, 1) if total > 0 else 0
        
        print(f"총 라인 수: {len(lines):,}")
        print(f"점수: {score:.1f}%")
        print(f"\n📊 우선순위별 점수:")
        
        priority_names = {
            "critical": "🔴 최우선",
            "high": "🟠 높음",
            "medium": "🟡 중간",
            "low": "🟢 낮음"
        }
        
        for priority in ["critical", "high", "medium", "low"]:
            p_score = priority_scores[priority]
            found_count = len(found_by_priority[priority])
            total_count = len(self.DESIGN_SECTIONS[priority])
            print(f"  {priority_names[priority]}: {p_score:5.1f}% ({found_count}/{total_count})")
        
        # 발견된 섹션 출력
        for priority in ["critical", "high", "medium", "low"]:
            if found_by_priority[priority]:
                print(f"\n✅ {priority_names[priority]} - 발견된 섹션:")
                for section, match in found_by_priority[priority].items():
                    icon = "✓" if match.match_type == 'exact' else "≈"
                    print(f"  {icon} {section:40s} → 라인 {match.line_number:4d}")
        
        # 누락된 섹션 출력
        for priority in ["critical", "high", "medium", "low"]:
            if missing_by_priority[priority]:
                print(f"\n❌ {priority_names[priority]} - 누락된 섹션:")
                for section in missing_by_priority[priority]:
                    print(f"  ✗ {section}")
                    # 유사한 섹션 제안
                    if section in similar_by_priority[priority]:
                        print(f"    💡 유사 섹션:")
                        for match in similar_by_priority[priority][section]:
                            print(f"       - 라인 {match.line_number:4d}: {match.title} (유사도: {match.similarity:.0%})")
        
        print()
        
        return {
            "score": round(score, 1),
            "found": found_by_priority,
            "missing": missing_by_priority,
            "similar": similar_by_priority,
            "priority_scores": priority_scores
        }

    
    def _analyze_tasks(self) -> Dict:
        """Tasks.md 분석 - 라인 번호 추적"""
        file_path = self.spec_path / "tasks.md"
        
        print(f"📋 Tasks.md")
        print(f"{'─'*80}")
        
        if not file_path.exists():
            print(f"❌ 파일 없음\n")
            return {"score": 0, "found": {}, "missing": []}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        content_lower = content.lower()
        found = {}
        missing = []
        
        # 1. 작업 구조: 체크박스 존재
        checkbox_pattern = r'- \[[ x]\]'
        checkboxes = [(m.start(), m.group()) for m in re.finditer(checkbox_pattern, content)]
        if checkboxes:
            first_line = content[:checkboxes[0][0]].count('\n') + 1
            found["작업 구조"] = f"라인 {first_line} (첫 체크박스)"
        else:
            missing.append("작업 구조")
        
        # 2. 체크박스 형식: 최소 5개
        checkbox_count = len(checkboxes)
        if checkbox_count >= 5:
            found["체크박스 형식"] = f"{checkbox_count}개 체크박스"
        else:
            missing.append("체크박스 형식")
        
        # 3. 명확한 목표
        if checkbox_count > 0:
            found["명확한 목표"] = f"{checkbox_count}개 작업 정의"
        else:
            missing.append("명확한 목표")
        
        # 4. 요구사항 참조
        req_pattern = r'_?requirements?:\s*\d+'
        req_matches = list(re.finditer(req_pattern, content_lower))
        if req_matches:
            first_line = content[:req_matches[0].start()].count('\n') + 1
            found["요구사항 참조"] = f"라인 {first_line} (첫 참조)"
        else:
            missing.append("요구사항 참조")
        
        # 5. 파일 경로 명시
        path_pattern = r'(\.py|\.ts|\.js|\.md|\.yaml|\.yml|/)'
        path_matches = list(re.finditer(path_pattern, content))
        if path_matches:
            first_line = content[:path_matches[0].start()].count('\n') + 1
            found["파일 경로 명시"] = f"라인 {first_line} (첫 경로)"
        else:
            missing.append("파일 경로 명시")
        
        # 6. 의존성 순서
        order_pattern = r'(\d+\.\d+|\d+\.|\bphase\b|\bstep\b)'
        order_matches = list(re.finditer(order_pattern, content_lower))
        if order_matches:
            first_line = content[:order_matches[0].start()].count('\n') + 1
            found["의존성 순서"] = f"라인 {first_line} (번호/Phase)"
        else:
            missing.append("의존성 순서")
        
        # 7. 선택적 작업 표시
        optional_pattern = r'(\*|optional)'
        optional_matches = list(re.finditer(optional_pattern, content_lower))
        if optional_matches:
            first_line = content[:optional_matches[0].start()].count('\n') + 1
            found["선택적 작업 표시"] = f"라인 {first_line} (*/optional)"
        else:
            missing.append("선택적 작업 표시")
        
        score = (len(found) / 7) * 100
        
        print(f"총 라인 수: {len(lines):,}")
        print(f"체크박스: {checkbox_count}개")
        print(f"점수: {score:.1f}%")
        
        if found:
            print(f"\n✅ 발견된 항목 ({len(found)}개):")
            for item, info in found.items():
                print(f"  ✓ {item:25s} → {info}")
        
        if missing:
            print(f"\n❌ 누락된 항목 ({len(missing)}개):")
            for item in missing:
                print(f"  ✗ {item}")
                # 제안
                if item == "선택적 작업 표시":
                    print(f"    💡 제안: 선택적 작업에 '*' 또는 'optional' 표시 추가")
                elif item == "요구사항 참조":
                    print(f"    💡 제안: '_Requirements: X.X' 형식으로 참조 추가")
        
        print()
        return {"score": round(score, 1), "found": found, "missing": missing}


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python analyze_spec_structure.py <spec_directory_path>")
        print("예시: python analyze_spec_structure.py .kiro/specs/policy-service")
        return
    
    spec_path = sys.argv[1]
    analyzer = SpecAnalyzer(spec_path)
    result = analyzer.analyze_spec()
    
    # 요약 출력
    print(f"📌 수정 권장사항:")
    if result['overall_score'] >= 95:
        print(f"  ✅ 목표 점수(95%) 달성! 추가 최적화는 선택사항입니다.")
    elif result['overall_score'] >= 90:
        print(f"  ⚠️  목표에 근접했습니다. 누락된 섹션을 보완하세요.")
    else:
        print(f"  ❌ 목표 점수(95%)에 미달. 재구성을 권장합니다.")
        
        # 우선순위별 권장사항
        if result['design']['priority_scores']['critical'] < 100:
            print(f"  🔴 최우선: Design.md의 critical 섹션을 먼저 보완하세요")
        if result['requirements']['score'] < 90:
            print(f"  📝 Requirements.md의 누락 섹션을 보완하세요")
        if result['tasks']['score'] < 90:
            print(f"  📋 Tasks.md의 구조와 상세 정보를 보완하세요")


if __name__ == "__main__":
    main()
