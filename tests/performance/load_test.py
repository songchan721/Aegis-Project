#!/usr/bin/env python3
"""
Aegis Shared Library 부하 테스트

이 스크립트는 동시성 환경에서의 성능을 측정합니다.
"""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
import json
import argparse

from aegis_shared.logging import configure_logging, get_logger


@dataclass
class LoadTestResult:
    """부하 테스트 결과"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    requests_per_second: float
    average_response_time: float
    min_response_time: float
    max_response_time: float
    percentile_95: float
    percentile_99: float
    error_rate: float


class LoadTester:
    """부하 테스트 실행기"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.logger = get_logger(__name__)
        self.session = None
        
        # 테스트 결과
        self.results: Dict[str, LoadTestResult] = {}
        
        # JWT 토큰 (테스트용)
        self.access_token = None
    
    async def setup(self):
        """테스트 환경 설정"""
        self.session = aiohttp.ClientSession()
        
        # 로그인하여 토큰 획득
        await self._login()
    
    async def teardown(self):
        """테스트 환경 정리"""
        if self.session:
            await self.session.close()
    
    async def _login(self):
        """로그인하여 JWT 토큰 획득"""
        try:
            login_data = {
                "email": "test@example.com",
                "password": "password"
            }
            
            async with self.session.post(
                f"{self.base_url}/auth/login",
                data=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    self.logger.info("Successfully obtained access token")
                else:
                    self.logger.warning("Failed to obtain access token, using mock token")
                    # 테스트용 모의 토큰 생성
                    from aegis_shared.auth import JWTHandler
                    jwt_handler = JWTHandler(secret_key="test-secret")
                    self.access_token = jwt_handler.create_access_token({
                        "user_id": "test-user",
                        "email": "test@example.com"
                    })
        
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            # 테스트용 모의 토큰 생성
            from aegis_shared.auth import JWTHandler
            jwt_handler = JWTHandler(secret_key="test-secret")
            self.access_token = jwt_handler.create_access_token({
                "user_id": "test-user",
                "email": "test@example.com"
            })
    
    def _get_headers(self) -> Dict[str, str]:
        """인증 헤더 생성"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP 요청 실행"""
        start_time = time.time()
        
        try:
            async with self.session.request(
                method, 
                f"{self.base_url}{url}",
                headers=self._get_headers(),
                **kwargs
            ) as response:
                end_time = time.time()
                
                return {
                    "success": True,
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "error": None
                }
        
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "status_code": 0,
                "response_time": end_time - start_time,
                "error": str(e)
            }
    
    async def _run_concurrent_requests(
        self, 
        request_func, 
        concurrent_users: int, 
        requests_per_user: int
    ) -> List[Dict[str, Any]]:
        """동시 요청 실행"""
        
        async def user_session():
            """단일 사용자 세션"""
            results = []
            for _ in range(requests_per_user):
                result = await request_func()
                results.append(result)
                # 요청 간 간격 (실제 사용자 행동 시뮬레이션)
                await asyncio.sleep(0.1)
            return results
        
        # 동시 사용자 세션 실행
        tasks = [user_session() for _ in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks)
        
        # 결과 평탄화
        all_results = []
        for user_result in user_results:
            all_results.extend(user_result)
        
        return all_results
    
    def _calculate_results(self, results: List[Dict[str, Any]]) -> LoadTestResult:
        """테스트 결과 계산"""
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = total_requests - successful_requests
        
        response_times = [r["response_time"] for r in results]
        total_time = sum(response_times)
        
        if total_requests > 0:
            requests_per_second = total_requests / max(total_time, 0.001)
            average_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # 백분위수 계산
            sorted_times = sorted(response_times)
            percentile_95 = sorted_times[int(0.95 * len(sorted_times))]
            percentile_99 = sorted_times[int(0.99 * len(sorted_times))]
            
            error_rate = (failed_requests / total_requests) * 100
        else:
            requests_per_second = 0
            average_response_time = 0
            min_response_time = 0
            max_response_time = 0
            percentile_95 = 0
            percentile_99 = 0
            error_rate = 100
        
        return LoadTestResult(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_time=total_time,
            requests_per_second=requests_per_second,
            average_response_time=average_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            error_rate=error_rate
        )
    
    async def test_health_endpoint(self, concurrent_users: int = 10, requests_per_user: int = 100):
        """헬스 체크 엔드포인트 부하 테스트"""
        self.logger.info(f"Testing health endpoint with {concurrent_users} users, {requests_per_user} requests each")
        
        async def health_request():
            return await self._make_request("GET", "/health")
        
        results = await self._run_concurrent_requests(
            health_request, 
            concurrent_users, 
            requests_per_user
        )
        
        self.results["health_endpoint"] = self._calculate_results(results)
        self.logger.info("Health endpoint test completed")
    
    async def test_user_creation(self, concurrent_users: int = 5, requests_per_user: int = 20):
        """사용자 생성 엔드포인트 부하 테스트"""
        self.logger.info(f"Testing user creation with {concurrent_users} users, {requests_per_user} requests each")
        
        request_counter = 0
        
        async def create_user_request():
            nonlocal request_counter
            request_counter += 1
            
            user_data = {
                "email": f"loadtest_{request_counter}_{time.time()}@example.com",
                "name": f"Load Test User {request_counter}",
                "phone": f"+1234567{request_counter:03d}"
            }
            
            return await self._make_request("POST", "/users", json=user_data)
        
        results = await self._run_concurrent_requests(
            create_user_request,
            concurrent_users,
            requests_per_user
        )
        
        self.results["user_creation"] = self._calculate_results(results)
        self.logger.info("User creation test completed")
    
    async def test_user_listing(self, concurrent_users: int = 20, requests_per_user: int = 50):
        """사용자 목록 조회 부하 테스트"""
        self.logger.info(f"Testing user listing with {concurrent_users} users, {requests_per_user} requests each")
        
        async def list_users_request():
            return await self._make_request("GET", "/users?skip=0&limit=10")
        
        results = await self._run_concurrent_requests(
            list_users_request,
            concurrent_users,
            requests_per_user
        )
        
        self.results["user_listing"] = self._calculate_results(results)
        self.logger.info("User listing test completed")
    
    async def test_cached_user_retrieval(self, concurrent_users: int = 15, requests_per_user: int = 100):
        """캐시된 사용자 조회 부하 테스트"""
        self.logger.info(f"Testing cached user retrieval with {concurrent_users} users, {requests_per_user} requests each")
        
        # 테스트용 사용자 ID (실제로는 존재하지 않을 수 있음)
        test_user_id = "test-user-123"
        
        async def cached_user_request():
            return await self._make_request("GET", f"/users/{test_user_id}/cached")
        
        results = await self._run_concurrent_requests(
            cached_user_request,
            concurrent_users,
            requests_per_user
        )
        
        self.results["cached_user_retrieval"] = self._calculate_results(results)
        self.logger.info("Cached user retrieval test completed")
    
    async def test_metrics_endpoint(self, concurrent_users: int = 5, requests_per_user: int = 50):
        """메트릭 엔드포인트 부하 테스트"""
        self.logger.info(f"Testing metrics endpoint with {concurrent_users} users, {requests_per_user} requests each")
        
        async def metrics_request():
            return await self._make_request("GET", "/metrics")
        
        results = await self._run_concurrent_requests(
            metrics_request,
            concurrent_users,
            requests_per_user
        )
        
        self.results["metrics_endpoint"] = self._calculate_results(results)
        self.logger.info("Metrics endpoint test completed")
    
    async def test_event_publishing(self, concurrent_users: int = 10, requests_per_user: int = 30):
        """이벤트 발행 부하 테스트"""
        self.logger.info(f"Testing event publishing with {concurrent_users} users, {requests_per_user} requests each")
        
        request_counter = 0
        
        async def publish_event_request():
            nonlocal request_counter
            request_counter += 1
            
            event_data = {
                "message": f"Load test event {request_counter} at {time.time()}"
            }
            
            return await self._make_request("POST", "/events/test", json=event_data)
        
        results = await self._run_concurrent_requests(
            publish_event_request,
            concurrent_users,
            requests_per_user
        )
        
        self.results["event_publishing"] = self._calculate_results(results)
        self.logger.info("Event publishing test completed")
    
    async def run_all_tests(self):
        """모든 부하 테스트 실행"""
        self.logger.info("Starting comprehensive load testing")
        
        await self.setup()
        
        try:
            # 각 테스트 실행
            await self.test_health_endpoint()
            await self.test_user_listing()
            await self.test_cached_user_retrieval()
            await self.test_metrics_endpoint()
            await self.test_user_creation()
            await self.test_event_publishing()
            
        finally:
            await self.teardown()
        
        self.logger.info("All load tests completed")
    
    def generate_report(self) -> Dict[str, Any]:
        """부하 테스트 결과 보고서 생성"""
        if not self.results:
            return {"error": "No load test results available"}
        
        total_requests = sum(r.total_requests for r in self.results.values())
        total_successful = sum(r.successful_requests for r in self.results.values())
        total_failed = sum(r.failed_requests for r in self.results.values())
        
        avg_rps = statistics.mean([r.requests_per_second for r in self.results.values()])
        avg_response_time = statistics.mean([r.average_response_time for r in self.results.values()])
        avg_error_rate = statistics.mean([r.error_rate for r in self.results.values()])
        
        report = {
            "summary": {
                "total_requests": total_requests,
                "successful_requests": total_successful,
                "failed_requests": total_failed,
                "overall_success_rate": (total_successful / total_requests * 100) if total_requests > 0 else 0,
                "average_requests_per_second": avg_rps,
                "average_response_time_ms": avg_response_time * 1000,
                "average_error_rate": avg_error_rate
            },
            "test_results": {}
        }
        
        for test_name, result in self.results.items():
            report["test_results"][test_name] = {
                "requests": {
                    "total": result.total_requests,
                    "successful": result.successful_requests,
                    "failed": result.failed_requests,
                    "error_rate_percent": result.error_rate
                },
                "performance": {
                    "requests_per_second": round(result.requests_per_second, 2),
                    "response_times_ms": {
                        "average": round(result.average_response_time * 1000, 2),
                        "min": round(result.min_response_time * 1000, 2),
                        "max": round(result.max_response_time * 1000, 2),
                        "95th_percentile": round(result.percentile_95 * 1000, 2),
                        "99th_percentile": round(result.percentile_99 * 1000, 2)
                    }
                }
            }
        
        # 성능 등급 계산
        report["performance_grade"] = self._calculate_performance_grade(avg_rps, avg_error_rate)
        
        return report
    
    def _calculate_performance_grade(self, avg_rps: float, avg_error_rate: float) -> str:
        """성능 등급 계산"""
        if avg_error_rate > 5:
            return "F"  # 에러율이 5% 이상이면 실패
        elif avg_rps >= 1000 and avg_error_rate < 1:
            return "A+"
        elif avg_rps >= 500 and avg_error_rate < 2:
            return "A"
        elif avg_rps >= 200 and avg_error_rate < 3:
            return "B"
        elif avg_rps >= 100 and avg_error_rate < 5:
            return "C"
        else:
            return "D"
    
    def save_report(self, filename: str = "load_test_report.json"):
        """보고서를 파일로 저장"""
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Load test report saved to {filename}")
    
    def print_summary(self):
        """부하 테스트 결과 요약 출력"""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("AEGIS SHARED LIBRARY LOAD TEST REPORT")
        print("="*80)
        
        summary = report["summary"]
        print(f"Total Requests: {summary['total_requests']:,}")
        print(f"Successful Requests: {summary['successful_requests']:,}")
        print(f"Failed Requests: {summary['failed_requests']:,}")
        print(f"Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"Average RPS: {summary['average_requests_per_second']:.2f}")
        print(f"Average Response Time: {summary['average_response_time_ms']:.2f} ms")
        print(f"Average Error Rate: {summary['average_error_rate']:.1f}%")
        print(f"Performance Grade: {report['performance_grade']}")
        
        print("\n" + "-"*80)
        print("DETAILED RESULTS")
        print("-"*80)
        
        for test_name, result in report["test_results"].items():
            print(f"\n{test_name.replace('_', ' ').title()}:")
            print(f"  Requests: {result['requests']['total']:,} "
                  f"(Success: {result['requests']['successful']:,}, "
                  f"Failed: {result['requests']['failed']:,})")
            print(f"  RPS: {result['performance']['requests_per_second']:.2f}")
            print(f"  Avg Response: {result['performance']['response_times_ms']['average']:.2f} ms")
            print(f"  95th Percentile: {result['performance']['response_times_ms']['95th_percentile']:.2f} ms")
            print(f"  Error Rate: {result['requests']['error_rate_percent']:.1f}%")
        
        print("\n" + "="*80)


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Aegis Shared Library Load Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the service")
    parser.add_argument("--output", default="load_test_report.json", help="Output report file")
    
    args = parser.parse_args()
    
    # 로깅 설정
    configure_logging(service_name="load-test", log_level="INFO")
    
    # 부하 테스트 실행
    load_tester = LoadTester(base_url=args.url)
    
    print(f"Starting Load Test for {args.url}")
    print("This may take several minutes to complete.\n")
    
    start_time = time.time()
    
    try:
        await load_tester.run_all_tests()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\nLoad test completed in {total_time:.2f} seconds")
        
        # 결과 출력
        load_tester.print_summary()
        
        # 보고서 저장
        load_tester.save_report(args.output)
        
    except Exception as e:
        print(f"Load test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))