#!/usr/bin/env python3
"""
Spec 문서 병합 유틸리티

여러 개의 part 파일 또는 두 개의 파일을 하나의 문서로 병합합니다.
모든 spec에서 재사용 가능합니다.

사용법:
    # Part 파일 병합
    python merge_spec_documents.py <spec_name> <document_type> [--backup]
    
    # 두 파일 직접 병합
    python merge_spec_documents.py <file1> <file2> [--output <output_file>]

예시:
    python merge_spec_documents.py policy-service design
    python merge_spec_documents.py user-service requirements --backup
    python merge_spec_documents.py design_new.md design_additional.md --output design.md
"""

import os
import sys
import glob
import shutil
from datetime import datetime
from pathlib import Path

def merge_documents(spec_name: str, doc_type: str, create_backup: bool = False):
    """
    Spec 문서 병합
    
    Args:
        spec_name: spec 이름 (예: policy-service, user-service)
        doc_type: 문서 타입 (design, requirements, tasks)
        create_backup: 기존 파일 백업 여부
    """
    # 경로 설정
    spec_dir = Path(f".kiro/specs/{spec_name}")
    
    if not spec_dir.exists():
        print(f"❌ 오류: {spec_dir} 디렉토리를 찾을 수 없습니다.")
        return False
    
    # part 파일 패턴
    part_pattern = f"{doc_type}_new_part*.md"
    part_files = sorted(glob.glob(str(spec_dir / part_pattern)))
    
    if not part_files:
        print(f"❌ 오류: {part_pattern} 패턴의 파일을 찾을 수 없습니다.")
        print(f"   경로: {spec_dir}")
        return False
    
    # 출력 파일
    output_file = spec_dir / f"{doc_type}.md"
    
    # 백업 생성
    if create_backup and output_file.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = spec_dir / f"{doc_type}.md.backup_{timestamp}"
        shutil.copy2(output_file, backup_file)
        print(f"📦 백업 생성: {backup_file.name}")
    
    # 병합 시작
    print()
    print("=" * 70)
    print(f"📄 {spec_name} - {doc_type}.md 병합 시작")
    print("=" * 70)
    print(f"출력 파일: {output_file}")
    print(f"병합할 파일 수: {len(part_files)}")
    print()
    
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for i, part_file in enumerate(part_files, 1):
                part_name = Path(part_file).name
                print(f"[{i}/{len(part_files)}] {part_name} 병합 중...")
                
                with open(part_file, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    outfile.write(content)
                    
                    # 마지막 파일이 아니면 구분을 위한 빈 줄 추가
                    if i < len(part_files):
                        outfile.write('\n\n')
                
                print(f"   ✅ 완료")
        
        print()
        print("=" * 70)
        print("✅ 모든 파일 병합 완료!")
        print("=" * 70)
        print()
        print(f"📄 출력 파일: {output_file}")
        print(f"📊 총 라인 수: {count_lines(output_file)}")
        print()
        
        # 정리 옵션
        print("다음 단계:")
        print(f"1. {output_file.name} 파일을 열어 내용을 확인하세요")
        print("2. 중복된 헤더나 불필요한 빈 줄이 있는지 확인하세요")
        print("3. 문서가 올바르게 렌더링되는지 확인하세요")
        print()
        
        # part 파일 정리 제안
        response = input("병합된 part 파일들을 삭제하시겠습니까? (y/N): ").strip().lower()
        if response == 'y':
            for part_file in part_files:
                os.remove(part_file)
                print(f"🗑️  삭제: {Path(part_file).name}")
            print("✅ part 파일 정리 완료")
        else:
            print("ℹ️  part 파일들이 유지됩니다.")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def count_lines(file_path: Path) -> int:
    """파일의 라인 수 계산"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except:
        return 0

def merge_two_files(file1: str, file2: str, output_file: str = None):
    """
    두 파일을 직접 병합
    
    Args:
        file1: 첫 번째 파일 경로
        file2: 두 번째 파일 경로
        output_file: 출력 파일 경로 (기본값: file1 덮어쓰기)
    """
    file1_path = Path(file1)
    file2_path = Path(file2)
    
    if not file1_path.exists():
        print(f"❌ 오류: {file1} 파일을 찾을 수 없습니다.")
        return False
    
    if not file2_path.exists():
        print(f"❌ 오류: {file2} 파일을 찾을 수 없습니다.")
        return False
    
    # 출력 파일 결정
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = file1_path
    
    print()
    print("=" * 70)
    print(f"📄 파일 병합 시작")
    print("=" * 70)
    print(f"파일 1: {file1_path.name}")
    print(f"파일 2: {file2_path.name}")
    print(f"출력: {output_path.name}")
    print()
    
    try:
        # 백업 생성 (출력 파일이 이미 존재하고 file1과 다른 경우)
        if output_path.exists() and output_path != file1_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = output_path.parent / f"{output_path.stem}.backup_{timestamp}{output_path.suffix}"
            shutil.copy2(output_path, backup_file)
            print(f"📦 백업 생성: {backup_file.name}")
        
        with open(output_path, 'w', encoding='utf-8') as outfile:
            # 첫 번째 파일 내용
            print(f"[1/2] {file1_path.name} 읽는 중...")
            with open(file1_path, 'r', encoding='utf-8') as f1:
                content1 = f1.read()
                outfile.write(content1)
                if not content1.endswith('\n'):
                    outfile.write('\n')
            print(f"   ✅ 완료")
            
            # 구분선 추가
            outfile.write('\n---\n\n')
            
            # 두 번째 파일 내용
            print(f"[2/2] {file2_path.name} 읽는 중...")
            with open(file2_path, 'r', encoding='utf-8') as f2:
                content2 = f2.read()
                # 두 번째 파일이 제목으로 시작하면 제목 제거
                lines = content2.split('\n')
                if lines and lines[0].startswith('# '):
                    # 첫 번째 제목 라인 건너뛰기
                    content2 = '\n'.join(lines[1:]).lstrip()
                outfile.write(content2)
            print(f"   ✅ 완료")
        
        print()
        print("=" * 70)
        print("✅ 파일 병합 완료!")
        print("=" * 70)
        print()
        print(f"📄 출력 파일: {output_path}")
        print(f"📊 총 라인 수: {count_lines(output_path)}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    if len(sys.argv) < 3:
        print("사용법:")
        print("  1. Part 파일 병합:")
        print("     python merge_spec_documents.py <spec_name> <document_type> [--backup]")
        print()
        print("  2. 두 파일 직접 병합:")
        print("     python merge_spec_documents.py <file1> <file2> [--output <output_file>]")
        print()
        print("예시:")
        print("  python merge_spec_documents.py policy-service design")
        print("  python merge_spec_documents.py user-service requirements --backup")
        print("  python merge_spec_documents.py design_new.md design.md")
        print("  python merge_spec_documents.py design_new.md design.md --output design_final.md")
        sys.exit(1)
    
    arg1 = sys.argv[1]
    arg2 = sys.argv[2]
    
    # 파일 경로인지 확인 (확장자가 .md인 경우)
    if arg1.endswith('.md') or Path(arg1).exists():
        # 두 파일 직접 병합 모드
        file1 = arg1
        file2 = arg2
        
        # --output 옵션 확인
        output_file = None
        if '--output' in sys.argv:
            output_idx = sys.argv.index('--output')
            if output_idx + 1 < len(sys.argv):
                output_file = sys.argv[output_idx + 1]
        
        success = merge_two_files(file1, file2, output_file)
    else:
        # Part 파일 병합 모드
        spec_name = arg1
        doc_type = arg2
        create_backup = '--backup' in sys.argv
        
        # 문서 타입 검증
        valid_types = ['design', 'requirements', 'tasks']
        if doc_type not in valid_types:
            print(f"❌ 오류: 유효하지 않은 문서 타입 '{doc_type}'")
            print(f"   유효한 타입: {', '.join(valid_types)}")
            sys.exit(1)
        
        success = merge_documents(spec_name, doc_type, create_backup)
    
    if success:
        print()
        print("🎉 병합 완료!")
        sys.exit(0)
    else:
        print()
        print("❌ 병합 실패")
        sys.exit(1)

if __name__ == "__main__":
    main()
