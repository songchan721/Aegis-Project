#!/usr/bin/env python3
"""
Private PyPI 배포 스크립트

Aegis Shared Library를 Private PyPI 서버에 배포하는 스크립트입니다.
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
import argparse


class PrivatePyPIDeployer:
    """Private PyPI 배포자"""
    
    def __init__(self, repository: str = "private-pypi"):
        self.repository = repository
        self.project_root = Path(__file__).parent.parent
        
    def check_poetry_config(self) -> bool:
        """Poetry 설정 확인"""
        print("🔍 Checking Poetry configuration...")
        
        try:
            result = subprocess.run(
                ["poetry", "config", "--list"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to get Poetry config: {result.stderr}")
                return False
            
            config_output = result.stdout
            
            # Repository 설정 확인
            repo_key = f"repositories.{self.repository}"
            if repo_key not in config_output:
                print(f"❌ Repository '{self.repository}' not configured")
                print(f"💡 Run: poetry config repositories.{self.repository} <URL>")
                return False
            
            # 인증 정보 확인
            auth_key = f"http-basic.{self.repository}"
            token_key = f"pypi-token.{self.repository}"
            
            if auth_key not in config_output and token_key not in config_output:
                print(f"❌ No credentials configured for '{self.repository}'")
                print(f"💡 Run: poetry config http-basic.{self.repository} <username> <password>")
                print(f"💡 Or: poetry config pypi-token.{self.repository} <token>")
                return False
            
            print("✅ Poetry configuration is valid")
            return True
            
        except Exception as e:
            print(f"❌ Error checking Poetry config: {e}")
            return False
    
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
    
    def bump_version(self, version_type: str) -> Optional[str]:
        """버전 업데이트"""
        valid_types = ["patch", "minor", "major", "prepatch", "preminor", "premajor", "prerelease"]
        
        if version_type not in valid_types:
            print(f"❌ Invalid version type: {version_type}")
            print(f"💡 Valid types: {', '.join(valid_types)}")
            return None
        
        print(f"📈 Bumping {version_type} version...")
        
        try:
            result = subprocess.run(
                ["poetry", "version", version_type],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to bump version: {result.stderr}")
                return None
            
            new_version = self.get_current_version()
            if new_version:
                print(f"✅ Version updated to {new_version}")
            
            return new_version
            
        except Exception as e:
            print(f"❌ Error bumping version: {e}")
            return None
    
    def build_package(self) -> bool:
        """패키지 빌드"""
        print("🏗️ Building package...")
        
        try:
            # 기존 빌드 아티팩트 정리
            dist_dir = self.project_root / "dist"
            if dist_dir.exists():
                import shutil
                shutil.rmtree(dist_dir)
            
            # 패키지 빌드
            result = subprocess.run(
                ["poetry", "build"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Build failed: {result.stderr}")
                return False
            
            # 빌드된 파일 확인
            if not dist_dir.exists():
                print("❌ Build failed: dist directory not found")
                return False
            
            built_files = list(dist_dir.glob("*"))
            if not built_files:
                print("❌ Build failed: no files in dist directory")
                return False
            
            print("✅ Package built successfully")
            print("📦 Built files:")
            for file in built_files:
                print(f"   - {file.name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Build error: {e}")
            return False
    
    def check_package_exists(self, version: str) -> bool:
        """패키지가 이미 존재하는지 확인"""
        print(f"🔍 Checking if version {version} already exists...")
        
        try:
            # pip index를 사용하여 패키지 존재 여부 확인
            result = subprocess.run(
                ["pip", "index", "versions", "aegis-shared", "--index-url", f"https://{self.repository}/simple/"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and version in result.stdout:
                print(f"⚠️ Version {version} already exists in repository")
                return True
            
            return False
            
        except Exception:
            # pip index가 지원되지 않는 경우 무시
            return False
    
    def deploy(self, force: bool = False) -> bool:
        """배포 실행"""
        current_version = self.get_current_version()
        if not current_version:
            return False
        
        # 패키지 존재 여부 확인
        if not force and self.check_package_exists(current_version):
            print(f"❌ Version {current_version} already exists. Use --force to override.")
            return False
        
        print(f"🚀 Deploying version {current_version} to {self.repository}...")
        
        try:
            result = subprocess.run(
                ["poetry", "publish", "--repository", self.repository],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Deployment failed: {result.stderr}")
                return False
            
            print("✅ Deployment successful!")
            print(f"📦 Package aegis-shared=={current_version} is now available")
            
            return True
            
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            return False
    
    def full_deploy(
        self, 
        version_bump: Optional[str] = None, 
        force: bool = False,
        skip_build: bool = False
    ) -> bool:
        """전체 배포 프로세스"""
        print("🚀 Starting deployment process...")
        
        # Poetry 설정 확인
        if not self.check_poetry_config():
            return False
        
        # 버전 업데이트 (선택적)
        if version_bump:
            new_version = self.bump_version(version_bump)
            if not new_version:
                return False
        
        # 패키지 빌드
        if not skip_build:
            if not self.build_package():
                return False
        
        # 배포
        return self.deploy(force=force)
    
    def setup_repository(self, url: str, username: str = None, password: str = None, token: str = None) -> bool:
        """Repository 설정"""
        print(f"⚙️ Setting up repository '{self.repository}'...")
        
        try:
            # Repository URL 설정
            result = subprocess.run(
                ["poetry", "config", f"repositories.{self.repository}", url],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to set repository URL: {result.stderr}")
                return False
            
            # 인증 정보 설정
            if token:
                result = subprocess.run(
                    ["poetry", "config", f"pypi-token.{self.repository}", token],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"❌ Failed to set token: {result.stderr}")
                    return False
                
                print("✅ Token authentication configured")
                
            elif username and password:
                result = subprocess.run(
                    ["poetry", "config", f"http-basic.{self.repository}", username, password],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"❌ Failed to set credentials: {result.stderr}")
                    return False
                
                print("✅ Basic authentication configured")
            
            print(f"✅ Repository '{self.repository}' configured successfully")
            return True
            
        except Exception as e:
            print(f"❌ Setup error: {e}")
            return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Deploy Aegis Shared Library to Private PyPI")
    
    parser.add_argument(
        "--repository", 
        default="private-pypi",
        help="Repository name (default: private-pypi)"
    )
    
    parser.add_argument(
        "--bump", 
        choices=["patch", "minor", "major", "prepatch", "preminor", "premajor", "prerelease"],
        help="Bump version before deployment"
    )
    
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Force deployment even if version exists"
    )
    
    parser.add_argument(
        "--skip-build", 
        action="store_true",
        help="Skip build step (use existing dist files)"
    )
    
    # Setup subcommand
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    setup_parser = subparsers.add_parser("setup", help="Setup repository configuration")
    setup_parser.add_argument("url", help="Repository URL")
    setup_parser.add_argument("--username", help="Username for basic auth")
    setup_parser.add_argument("--password", help="Password for basic auth")
    setup_parser.add_argument("--token", help="API token for token auth")
    
    args = parser.parse_args()
    
    deployer = PrivatePyPIDeployer(repository=args.repository)
    
    try:
        if args.command == "setup":
            success = deployer.setup_repository(
                url=args.url,
                username=args.username,
                password=args.password,
                token=args.token
            )
        else:
            success = deployer.full_deploy(
                version_bump=args.bump,
                force=args.force,
                skip_build=args.skip_build
            )
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()