#!/usr/bin/env python3
"""모든 Spec 분석 스크립트"""

from pathlib import Path
from analyze_spec_structure import SpecAnalyzer


def main():
    """모든 스펙 분석"""
    specs_dir = Path('.kiro/specs')
    
    if not specs_dir.exists():
        print(f"❌ {specs_dir} 디렉토리를 찾을 수 없습니다.")
        return
    
    # 모든 스펙 디렉토리 찾기
    spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]
    spec_dirs.sort()
    
    print(f"\n{'='*80}")
    print(f"📊 전체 Spec 분석 ({len(spec_dirs)}개)")
    print(f"{'='*80}\n")
    
    results = []
    
    for spec_dir in spec_dirs:
        analyzer = SpecAnalyzer(str(spec_dir))
        result = analyzer.analyze_spec()
        results.append(result)
        print(f"\n{'-'*80}\n")
    
    # 전체 요약
    print(f"\n{'='*80}")
    print(f"📈 전체 요약")
    print(f"{'='*80}\n")
    
    print(f"{'Spec':30s} {'전체':>8s} {'Req':>8s} {'Design':>8s} {'Tasks':>8s}")
    print(f"{'-'*80}")
    
    for result in results:
        spec_name = result['spec_name']
        overall = result['overall_score']
        req = result['requirements']['score']
        design = result['design']['score']
        tasks = result['tasks']['score']
        
        # 상태 아이콘
        if overall >= 95:
            icon = "✅"
        elif overall >= 90:
            icon = "⚠️ "
        else:
            icon = "❌"
        
        print(f"{icon} {spec_name:27s} {overall:7.1f}% {req:7.1f}% {design:7.1f}% {tasks:7.1f}%")
    
    # 통계
    avg_overall = sum(r['overall_score'] for r in results) / len(results)
    avg_req = sum(r['requirements']['score'] for r in results) / len(results)
    avg_design = sum(r['design']['score'] for r in results) / len(results)
    avg_tasks = sum(r['tasks']['score'] for r in results) / len(results)
    
    print(f"{'-'*80}")
    print(f"{'평균':30s} {avg_overall:7.1f}% {avg_req:7.1f}% {avg_design:7.1f}% {avg_tasks:7.1f}%")
    
    # 목표 달성 현황
    target_met = sum(1 for r in results if r['overall_score'] >= 95)
    near_target = sum(1 for r in results if 90 <= r['overall_score'] < 95)
    needs_work = sum(1 for r in results if r['overall_score'] < 90)
    
    print(f"\n📊 목표 달성 현황:")
    print(f"  ✅ 목표 달성 (≥95%): {target_met}/{len(results)}")
    print(f"  ⚠️  목표 근접 (90-95%): {near_target}/{len(results)}")
    print(f"  ❌ 보완 필요 (<90%): {needs_work}/{len(results)}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
