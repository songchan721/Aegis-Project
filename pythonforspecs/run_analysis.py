#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from analyze_spec_structure import SpecAnalyzer

# policy-service 분석
analyzer = SpecAnalyzer('.kiro/specs/policy-service')
result = analyzer.analyze_spec()

print(f"\n최종 결과:")
print(f"  Spec: {result['spec_name']}")
print(f"  전체 점수: {result['overall_score']}%")
