#!/usr/bin/env python3
"""
Aegis Shared Library 빌드 스크립트

이 스크립트는 패키지 빌드, 테스트, 배포를 자동화합니다.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import List, Optional


class BuildError(Exception):
    """빌드 관련 에러"""
    pass


class AegisBuildTool:
    """Aegis Shared Library 빌드 도구"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.dist_dir = self.project_root / "dist"
        
    def run_command(self, command: List[str], cwd: Optional[Path] = None) -> None:
        """명령어 실행"""
        if cwd is None:
            cwd = self.project_root
            
        print(f"Running: {' '.join(command)}")
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            raise BuildError(f"Command failed: {' '.join(command)}")
        
        if result.stdout:
            print(result.stdout)
    
    def clean(self) -> None:
        """빌드 아티팩트 정리"""
        print("🧹 Cleaning build artifacts...")
        
        # dist 디렉토리 정리
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        
        # __pycache__ 디렉토리 정리
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)
        
        # .pyc 파일 정리
        for pyc_file in self.project_root.rglob("*.pyc"):
            pyc_file.unlink()
        
        # 테스트 커버리지 파일 정리
        coverage_files = [".coverage", "htmlcov"]
        for file_or_dir in coverage_files:
            path = self.project_root / file_or_dir
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        
        print("✅ Clean completed")
    
    def install_dependencies(self) -> None:
        """의존성 설치"""
        print("📦 Installing dependencies...")
        self.run_command(["poetry", "install"])
        print("✅ Dependencies installed")
    
    def lint(self) -> None:
        """코드 린팅"""
        print("🔍 Running linting...")
        
        # Black 포맷팅 체크
        try:
            self.run_command(["poetry", "run", "black", "--check", "aegis_shared/"])
            print("✅ Black formatting check passed")
        except BuildError:
            print("❌ Black formatting check failed")
            print("Run 'poetry run black aegis_shared/' to fix formatting")
            raise
        
        # isort 체크
        try:
            self.run_command(["poetry", "run", "isort", "--check-only", "aegis_shared/"])
            print("✅ isort check passed")
        except BuildError:
            print("❌ isort check failed")
            print("Run 'poetry run isort aegis_shared/' to fix imports")
            raise
    
    def type_check(self) -> None:
        """타입 체크"""
        print("🔍 Running type checking...")
        try:
            self.run_command(["poetry", "run", "mypy", "aegis_shared/"])
            print("✅ Type checking passed")
        except BuildError:
            print("❌ Type checking failed")
            raise
    
    def test(self, coverage: bool = True) -> None:
        """테스트 실행"""
        print("🧪 Running tests...")
        
        command = ["poetry", "run", "pytest"]
        if coverage:
            command.extend(["--cov=aegis_shared", "--cov-report=term-missing", "--cov-report=html"])
        
        command.extend(["-v", "aegis_shared/tests/"])
        
        try:
            self.run_command(command)
            print("✅ Tests passed")
        except BuildError:
            print("❌ Tests failed")
            raise
    
    def build_package(self) -> None:
        """패키지 빌드"""
        print("🏗️ Building package...")
        
        # Poetry를 사용하여 빌드
        self.run_command(["poetry", "build"])
        
        # 빌드된 파일 확인
        if not self.dist_dir.exists():
            raise BuildError("Build failed: dist directory not found")
        
        built_files = list(self.dist_dir.glob("*"))
        if not built_files:
            raise BuildError("Build failed: no files in dist directory")
        
        print("✅ Package built successfully")
        print("Built files:")
        for file in built_files:
            print(f"  - {file.name}")
    
    def check_version(self) -> str:
        """버전 확인"""
        result = subprocess.run(
            ["poetry", "version", "--short"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise BuildError("Failed to get version")
        
        return result.stdout.strip()
    
    def bump_version(self, version_type: str) -> None:
        """버전 업데이트"""
        print(f"📈 Bumping {version_type} version...")
        
        valid_types = ["patch", "minor", "major"]
        if version_type not in valid_types:
            raise BuildError(f"Invalid version type: {version_type}. Must be one of {valid_types}")
        
        self.run_command(["poetry", "version", version_type])
        
        new_version = self.check_version()
        print(f"✅ Version updated to {new_version}")
    
    def publish_test(self) -> None:
        """테스트 PyPI에 배포"""
        print("🚀 Publishing to Test PyPI...")
        
        self.run_command([
            "poetry", "publish",
            "--repository", "testpypi",
            "--username", "__token__"
        ])
        
        print("✅ Published to Test PyPI")
    
    def publish(self) -> None:
        """PyPI에 배포"""
        print("🚀 Publishing to PyPI...")
        
        self.run_command([
            "poetry", "publish",
            "--username", "__token__"
        ])
        
        print("✅ Published to PyPI")
    
    def publish_private(self, repository: str = "private-pypi") -> None:
        """Private PyPI에 배포"""
        print(f"🚀 Publishing to Private PyPI ({repository})...")
        
        self.run_command([
            "poetry", "publish",
            "--repository", repository
        ])
        
        print(f"✅ Published to Private PyPI ({repository})")
    
    def full_build(self, skip_tests: bool = False) -> None:
        """전체 빌드 프로세스"""
        print("🚀 Starting full build process...")
        
        try:
            self.clean()
            self.install_dependencies()
            
            if not skip_tests:
                self.lint()
                self.type_check()
                self.test()
            
            self.build_package()
            
            version = self.check_version()
            print(f"🎉 Build completed successfully! Version: {version}")
            
        except BuildError as e:
            print(f"❌ Build failed: {e}")
            sys.exit(1)


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aegis Shared Library Build Tool")
    parser.add_argument("command", choices=[
        "clean", "install", "lint", "type-check", "test", "build", 
        "version", "bump-patch", "bump-minor", "bump-major",
        "publish-test", "publish", "publish-private", "full-build"
    ], help="Command to execute")
    parser.add_argument("--repository", default="private-pypi", help="Repository name for private publishing")
    parser.add_argument("--skip-tests", action="store_true", help="Skip tests during full build")
    
    args = parser.parse_args()
    
    build_tool = AegisBuildTool()
    
    try:
        if args.command == "clean":
            build_tool.clean()
        elif args.command == "install":
            build_tool.install_dependencies()
        elif args.command == "lint":
            build_tool.lint()
        elif args.command == "type-check":
            build_tool.type_check()
        elif args.command == "test":
            build_tool.test()
        elif args.command == "build":
            build_tool.build_package()
        elif args.command == "version":
            version = build_tool.check_version()
            print(f"Current version: {version}")
        elif args.command == "bump-patch":
            build_tool.bump_version("patch")
        elif args.command == "bump-minor":
            build_tool.bump_version("minor")
        elif args.command == "bump-major":
            build_tool.bump_version("major")
        elif args.command == "publish-test":
            build_tool.publish_test()
        elif args.command == "publish":
            build_tool.publish()
        elif args.command == "publish-private":
            build_tool.publish_private(repository=args.repository)
        elif args.command == "full-build":
            build_tool.full_build(skip_tests=args.skip_tests)
            
    except KeyboardInterrupt:
        print("\n❌ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()