#!/usr/bin/env python3
"""
버전 관리 자동화 스크립트

Aegis Shared Library의 버전을 자동으로 관리하고 배포하는 스크립트입니다.
"""

import subprocess
import sys
import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import argparse


class VersionManager:
    """버전 관리자"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.changelog_path = self.project_root / "CHANGELOG.md"
        
    def get_current_version(self) -> Optional[str]:
        """현재 버전 조회"""
        try:
            result = subprocess.run(
                ["poetry", "version", "--short"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"❌ Failed to get version: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting version: {e}")
            return None
    
    def parse_version(self, version: str) -> Tuple[int, int, int, Optional[str]]:
        """버전 문자열 파싱"""
        # 정규식으로 버전 파싱 (예: 1.2.3-alpha.1)
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$'
        match = re.match(pattern, version)
        
        if not match:
            raise ValueError(f"Invalid version format: {version}")
        
        major, minor, patch, prerelease = match.groups()
        return int(major), int(minor), int(patch), prerelease
    
    def format_version(self, major: int, minor: int, patch: int, prerelease: Optional[str] = None) -> str:
        """버전 문자열 생성"""
        version = f"{major}.{minor}.{patch}"
        if prerelease:
            version += f"-{prerelease}"
        return version
    
    def bump_version(self, version_type: str, prerelease_type: Optional[str] = None) -> Optional[str]:
        """버전 업데이트"""
        current_version = self.get_current_version()
        if not current_version:
            return None
        
        try:
            major, minor, patch, current_prerelease = self.parse_version(current_version)
            
            if version_type == "major":
                major += 1
                minor = 0
                patch = 0
                prerelease = None
            elif version_type == "minor":
                minor += 1
                patch = 0
                prerelease = None
            elif version_type == "patch":
                patch += 1
                prerelease = None
            elif version_type == "prerelease":
                if current_prerelease:
                    # 기존 prerelease 버전 증가
                    if "." in current_prerelease:
                        prefix, num = current_prerelease.rsplit(".", 1)
                        try:
                            new_num = int(num) + 1
                            prerelease = f"{prefix}.{new_num}"
                        except ValueError:
                            prerelease = f"{current_prerelease}.1"
                    else:
                        prerelease = f"{current_prerelease}.1"
                else:
                    # 새로운 prerelease 시작
                    prerelease_type = prerelease_type or "alpha"
                    prerelease = f"{prerelease_type}.1"
            else:
                print(f"❌ Invalid version type: {version_type}")
                return None
            
            new_version = self.format_version(major, minor, patch, prerelease)
            
            # Poetry로 버전 업데이트
            result = subprocess.run(
                ["poetry", "version", new_version],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to update version: {result.stderr}")
                return None
            
            print(f"✅ Version updated: {current_version} → {new_version}")
            return new_version
            
        except Exception as e:
            print(f"❌ Error updating version: {e}")
            return None
    
    def get_git_commits_since_tag(self, tag: Optional[str] = None) -> List[str]:
        """특정 태그 이후의 커밋 메시지 조회"""
        try:
            if tag:
                cmd = ["git", "log", f"{tag}..HEAD", "--oneline", "--no-merges"]
            else:
                # 최근 태그 찾기
                result = subprocess.run(
                    ["git", "describe", "--tags", "--abbrev=0"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                if result.returncode == 0:
                    last_tag = result.stdout.strip()
                    cmd = ["git", "log", f"{last_tag}..HEAD", "--oneline", "--no-merges"]
                else:
                    # 태그가 없으면 전체 로그
                    cmd = ["git", "log", "--oneline", "--no-merges"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.split('\n') if line.strip()]
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error getting git commits: {e}")
            return []
    
    def categorize_commits(self, commits: List[str]) -> Dict[str, List[str]]:
        """커밋을 카테고리별로 분류"""
        categories = {
            "breaking": [],
            "features": [],
            "fixes": [],
            "improvements": [],
            "docs": [],
            "tests": [],
            "chore": [],
            "other": []
        }
        
        for commit in commits:
            commit_lower = commit.lower()
            
            if any(keyword in commit_lower for keyword in ["breaking", "break:", "!:"]):
                categories["breaking"].append(commit)
            elif any(keyword in commit_lower for keyword in ["feat:", "feature:", "add:"]):
                categories["features"].append(commit)
            elif any(keyword in commit_lower for keyword in ["fix:", "bug:", "hotfix:"]):
                categories["fixes"].append(commit)
            elif any(keyword in commit_lower for keyword in ["improve:", "enhance:", "refactor:"]):
                categories["improvements"].append(commit)
            elif any(keyword in commit_lower for keyword in ["docs:", "doc:", "readme:"]):
                categories["docs"].append(commit)
            elif any(keyword in commit_lower for keyword in ["test:", "tests:"]):
                categories["tests"].append(commit)
            elif any(keyword in commit_lower for keyword in ["chore:", "build:", "ci:"]):
                categories["chore"].append(commit)
            else:
                categories["other"].append(commit)
        
        return categories
    
    def suggest_version_bump(self, commits: List[str]) -> str:
        """커밋 내용을 기반으로 버전 업데이트 타입 제안"""
        categories = self.categorize_commits(commits)
        
        if categories["breaking"]:
            return "major"
        elif categories["features"]:
            return "minor"
        elif categories["fixes"] or categories["improvements"]:
            return "patch"
        else:
            return "patch"  # 기본값
    
    def update_changelog(self, version: str, commits: List[str]) -> bool:
        """CHANGELOG.md 업데이트"""
        try:
            categories = self.categorize_commits(commits)
            
            # 새로운 변경사항 생성
            new_entry = f"\n## [{version}] - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            
            if categories["breaking"]:
                new_entry += "### 💥 Breaking Changes\n\n"
                for commit in categories["breaking"]:
                    new_entry += f"- {commit}\n"
                new_entry += "\n"
            
            if categories["features"]:
                new_entry += "### ✨ New Features\n\n"
                for commit in categories["features"]:
                    new_entry += f"- {commit}\n"
                new_entry += "\n"
            
            if categories["fixes"]:
                new_entry += "### 🐛 Bug Fixes\n\n"
                for commit in categories["fixes"]:
                    new_entry += f"- {commit}\n"
                new_entry += "\n"
            
            if categories["improvements"]:
                new_entry += "### 🚀 Improvements\n\n"
                for commit in categories["improvements"]:
                    new_entry += f"- {commit}\n"
                new_entry += "\n"
            
            if categories["docs"]:
                new_entry += "### 📚 Documentation\n\n"
                for commit in categories["docs"]:
                    new_entry += f"- {commit}\n"
                new_entry += "\n"
            
            if categories["tests"]:
                new_entry += "### 🧪 Tests\n\n"
                for commit in categories["tests"]:
                    new_entry += f"- {commit}\n"
                new_entry += "\n"
            
            if categories["chore"]:
                new_entry += "### 🔧 Maintenance\n\n"
                for commit in categories["chore"]:
                    new_entry += f"- {commit}\n"
                new_entry += "\n"
            
            if categories["other"]:
                new_entry += "### 📝 Other Changes\n\n"
                for commit in categories["other"]:
                    new_entry += f"- {commit}\n"
                new_entry += "\n"
            
            # CHANGELOG.md 읽기
            if self.changelog_path.exists():
                with open(self.changelog_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
            
            # 새로운 엔트리 삽입 (첫 번째 ## 섹션 앞에)
            lines = content.split('\n')
            insert_index = 0
            
            for i, line in enumerate(lines):
                if line.startswith('## [') and i > 0:
                    insert_index = i
                    break
            
            if insert_index > 0:
                lines.insert(insert_index, new_entry.rstrip())
            else:
                lines.append(new_entry.rstrip())
            
            # 파일 쓰기
            with open(self.changelog_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print(f"✅ CHANGELOG.md updated for version {version}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating changelog: {e}")
            return False
    
    def create_git_tag(self, version: str, message: Optional[str] = None) -> bool:
        """Git 태그 생성"""
        try:
            tag_name = f"v{version}"
            tag_message = message or f"Release version {version}"
            
            result = subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", tag_message],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to create tag: {result.stderr}")
                return False
            
            print(f"✅ Git tag created: {tag_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating git tag: {e}")
            return False
    
    def push_tag(self, version: str) -> bool:
        """Git 태그 푸시"""
        try:
            tag_name = f"v{version}"
            
            result = subprocess.run(
                ["git", "push", "origin", tag_name],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to push tag: {result.stderr}")
                return False
            
            print(f"✅ Git tag pushed: {tag_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error pushing git tag: {e}")
            return False
    
    def release(
        self, 
        version_type: str, 
        prerelease_type: Optional[str] = None,
        skip_changelog: bool = False,
        skip_tag: bool = False,
        push_tag: bool = False
    ) -> Optional[str]:
        """전체 릴리스 프로세스"""
        print("🚀 Starting release process...")
        
        # 현재 상태 확인
        current_version = self.get_current_version()
        if not current_version:
            return None
        
        print(f"📋 Current version: {current_version}")
        
        # 커밋 조회
        commits = self.get_git_commits_since_tag()
        if commits:
            print(f"📝 Found {len(commits)} commits since last release")
            
            # 자동 버전 타입 제안
            if version_type == "auto":
                suggested_type = self.suggest_version_bump(commits)
                print(f"💡 Suggested version bump: {suggested_type}")
                version_type = suggested_type
        else:
            print("📝 No new commits found")
        
        # 버전 업데이트
        new_version = self.bump_version(version_type, prerelease_type)
        if not new_version:
            return None
        
        # CHANGELOG 업데이트
        if not skip_changelog and commits:
            if not self.update_changelog(new_version, commits):
                print("⚠️ Failed to update changelog, continuing...")
        
        # Git 태그 생성
        if not skip_tag:
            if not self.create_git_tag(new_version):
                print("⚠️ Failed to create git tag, continuing...")
            elif push_tag:
                if not self.push_tag(new_version):
                    print("⚠️ Failed to push git tag, continuing...")
        
        print(f"🎉 Release completed: {new_version}")
        return new_version


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Aegis Shared Library Version Manager")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # version 명령어
    version_parser = subparsers.add_parser("version", help="Show current version")
    
    # bump 명령어
    bump_parser = subparsers.add_parser("bump", help="Bump version")
    bump_parser.add_argument(
        "type", 
        choices=["major", "minor", "patch", "prerelease", "auto"],
        help="Version bump type"
    )
    bump_parser.add_argument(
        "--prerelease-type",
        choices=["alpha", "beta", "rc"],
        default="alpha",
        help="Prerelease type (default: alpha)"
    )
    
    # release 명령어
    release_parser = subparsers.add_parser("release", help="Full release process")
    release_parser.add_argument(
        "type",
        choices=["major", "minor", "patch", "prerelease", "auto"],
        help="Version bump type"
    )
    release_parser.add_argument(
        "--prerelease-type",
        choices=["alpha", "beta", "rc"],
        default="alpha",
        help="Prerelease type (default: alpha)"
    )
    release_parser.add_argument(
        "--skip-changelog",
        action="store_true",
        help="Skip changelog update"
    )
    release_parser.add_argument(
        "--skip-tag",
        action="store_true",
        help="Skip git tag creation"
    )
    release_parser.add_argument(
        "--push-tag",
        action="store_true",
        help="Push git tag to remote"
    )
    
    # changelog 명령어
    changelog_parser = subparsers.add_parser("changelog", help="Update changelog")
    changelog_parser.add_argument("version", help="Version for changelog entry")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    version_manager = VersionManager()
    
    try:
        if args.command == "version":
            version = version_manager.get_current_version()
            if version:
                print(f"Current version: {version}")
            else:
                sys.exit(1)
        
        elif args.command == "bump":
            new_version = version_manager.bump_version(args.type, args.prerelease_type)
            if not new_version:
                sys.exit(1)
        
        elif args.command == "release":
            new_version = version_manager.release(
                version_type=args.type,
                prerelease_type=args.prerelease_type,
                skip_changelog=args.skip_changelog,
                skip_tag=args.skip_tag,
                push_tag=args.push_tag
            )
            if not new_version:
                sys.exit(1)
        
        elif args.command == "changelog":
            commits = version_manager.get_git_commits_since_tag()
            if not version_manager.update_changelog(args.version, commits):
                sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()