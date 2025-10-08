# S.C.O.R.E. 프레임워크 상세 명세

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-CMP-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. S.C.O.R.E. 프레임워크 개요

### 1.1. 정의 및 목적
**S.C.O.R.E. 프레임워크**는 이지스 시스템의 모든 AI 판단과 추천 결과를 정량적으로 측정하고 설명 가능하게 만드는 핵심 방법론입니다. 이 프레임워크는 "블랙박스" AI를 "화이트박스" AI로 전환하여 사용자와 시스템 운영자 모두에게 완전한 투명성을 제공합니다.

### 1.2. 5가지 핵심 원칙

#### **S - Specificity (구체성)**
- **정의**: 모든 입력과 출력이 명확하고 구체적으로 정의되어야 함
- **목적**: 모호함을 제거하고 정확한 처리 보장
- **측정**: 입출력 스키마 준수율, 데이터 타입 정확성

#### **C - Consistency (일관성)**
- **정의**: 동일한 입력에 대해 항상 동일한 결과를 보장
- **목적**: 시스템의 신뢰성과 예측 가능성 확보
- **측정**: 재현율, 결과 변동성 지표

#### **O - Observability (관찰가능성)**
- **정의**: 모든 처리 과정과 의사결정 단계를 추적하고 관찰 가능
- **목적**: 시스템 동작의 완전한 가시성 제공
- **측정**: 로그 커버리지, 메트릭 수집률, 추적 완성도

#### **R - Reproducibility (재현가능성)**
- **정의**: 동일한 조건에서 결과를 완벽하게 재현할 수 있어야 함
- **목적**: 디버깅, 감사, 품질 보증 지원
- **측정**: 재현 성공률, 환경 일관성 지표

#### **E - Explainability (설명가능성)**
- **정의**: 모든 판단의 근거와 과정을 사용자가 이해할 수 있도록 설명
- **목적**: 사용자 신뢰 구축 및 의사결정 지원
- **측정**: 설명 완성도, 사용자 이해도, 근거 정확성

## 2. 각 원칙별 구현 상세

### 2.1. Specificity (구체성) 구현

#### 데이터 스키마 정의
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class BusinessType(str, Enum):
    SMALL_BUSINESS = "소상공인"
    MEDIUM_ENTERPRISE = "중소기업"
    INDIVIDUAL = "개인사업자"

class UserProfile(BaseModel):
    """사용자 프로필 - 구체적 스키마 정의"""
    user_id: str = Field(..., description="사용자 고유 ID")
    business_type: BusinessType = Field(..., description="사업자 유형")
    industry_code: str = Field(..., regex=r"^\d{2,5}$", description="한국표준산업분류코드")
    annual_revenue: Optional[int] = Field(None, ge=0, description="연매출액 (원)")
    employee_count: int = Field(..., ge=0, le=1000, description="직원 수")
    establishment_date: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$", description="설립일 (YYYY-MM-DD)")
    region_code: str = Field(..., regex=r"^\d{2}$", description="지역코드")

class RecommendationRequest(BaseModel):
    """추천 요청 - 명확한 입력 정의"""
    user_profile: UserProfile
    query: str = Field(..., min_length=1, max_length=500, description="자연어 쿼리")
    max_results: int = Field(10, ge=1, le=50, description="최대 결과 수")
    include_expired: bool = Field(False, description="만료된 정책 포함 여부")

class PolicyRecommendation(BaseModel):
    """정책 추천 결과 - 구체적 출력 정의"""
    policy_id: str = Field(..., description="정책 고유 ID")
    title: str = Field(..., description="정책명")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="관련성 점수")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="신뢰도 점수")
    explanation: str = Field(..., min_length=10, description="추천 근거 설명")
```

#### 입출력 검증 시스템
```python
class SpecificityValidator:
    """구체성 원칙 검증기"""
    
    def validate_input(self, data: dict, schema: BaseModel) -> tuple[bool, List[str]]:
        """입력 데이터의 구체성 검증"""
        errors = []
        
        try:
            validated_data = schema.parse_obj(data)
            return True, []
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                errors.append(f"Field '{field}': {error['msg']}")
            return False, errors
    
    def validate_output(self, result: dict) -> dict:
        """출력 결과의 구체성 메트릭 계산"""
        metrics = {
            "schema_compliance": self._check_schema_compliance(result),
            "field_completeness": self._calculate_completeness(result),
            "data_type_accuracy": self._check_data_types(result)
        }
        return metrics
```

### 2.2. Consistency (일관성) 구현

#### 결정론적 처리 보장
```python
import hashlib
import json
from typing import Any

class ConsistencyManager:
    """일관성 관리자"""
    
    def __init__(self):
        self.seed_value = 42  # 고정 시드값
        self.cache = {}
    
    def generate_deterministic_hash(self, input_data: dict) -> str:
        """입력 데이터의 결정론적 해시 생성"""
        # 딕셔너리를 정렬하여 일관된 해시 생성
        sorted_data = json.dumps(input_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def ensure_consistent_processing(self, input_data: dict, processor_func) -> Any:
        """일관된 처리 보장"""
        input_hash = self.generate_deterministic_hash(input_data)
        
        # 캐시된 결과가 있으면 반환
        if input_hash in self.cache:
            return self.cache[input_hash]
        
        # 시드값 설정으로 일관된 랜덤 결과 보장
        import random
        import numpy as np
        random.seed(self.seed_value)
        np.random.seed(self.seed_value)
        
        # 처리 실행
        result = processor_func(input_data)
        
        # 결과 캐싱
        self.cache[input_hash] = result
        return result
```

#### 일관성 메트릭 측정
```python
class ConsistencyMetrics:
    """일관성 메트릭 측정"""
    
    def measure_reproducibility(self, input_data: dict, processor_func, iterations: int = 10) -> dict:
        """재현성 측정"""
        results = []
        
        for _ in range(iterations):
            result = processor_func(input_data)
            results.append(result)
        
        # 결과 일관성 분석
        consistency_score = self._calculate_consistency_score(results)
        variance = self._calculate_variance(results)
        
        return {
            "consistency_score": consistency_score,
            "variance": variance,
            "identical_results": len(set(str(r) for r in results)) == 1
        }
```

### 2.3. Observability (관찰가능성) 구현

#### 포괄적 로깅 시스템
```python
import logging
import json
from datetime import datetime
from typing import Dict, Any
from contextlib import contextmanager

class ObservabilityLogger:
    """관찰가능성 로거"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.current_context = {}
    
    @contextmanager
    def trace_operation(self, operation_name: str, **context):
        """작업 추적 컨텍스트"""
        trace_id = self._generate_trace_id()
        start_time = datetime.utcnow()
        
        self.current_context.update({
            "trace_id": trace_id,
            "operation": operation_name,
            "start_time": start_time.isoformat(),
            **context
        })
        
        self.logger.info(f"Operation started: {operation_name}", extra=self.current_context)
        
        try:
            yield trace_id
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Operation completed: {operation_name}", extra={
                **self.current_context,
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "status": "success"
            })
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Operation failed: {operation_name}", extra={
                **self.current_context,
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "status": "error",
                "error_message": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    def log_decision_point(self, decision: str, factors: Dict[str, Any], result: Any):
        """의사결정 지점 로깅"""
        self.logger.info("Decision point", extra={
            **self.current_context,
            "decision_type": decision,
            "input_factors": factors,
            "decision_result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
```

#### 메트릭 수집 시스템
```python
from prometheus_client import Counter, Histogram, Gauge, Summary
from typing import Dict

class ObservabilityMetrics:
    """관찰가능성 메트릭"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        
        # 비즈니스 메트릭
        self.recommendation_requests = Counter(
            'recommendation_requests_total',
            'Total recommendation requests',
            ['service', 'user_type', 'query_type']
        )
        
        self.recommendation_latency = Histogram(
            'recommendation_duration_seconds',
            'Recommendation generation time',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        self.score_distribution = Histogram(
            'recommendation_scores',
            'Distribution of recommendation scores',
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        # 품질 메트릭
        self.explanation_completeness = Gauge(
            'explanation_completeness_ratio',
            'Ratio of complete explanations'
        )
        
        self.consistency_score = Gauge(
            'consistency_score',
            'Current consistency score'
        )
    
    def record_recommendation(self, user_type: str, query_type: str, 
                            duration: float, scores: List[float]):
        """추천 메트릭 기록"""
        self.recommendation_requests.labels(
            service=self.service_name,
            user_type=user_type,
            query_type=query_type
        ).inc()
        
        self.recommendation_latency.observe(duration)
        
        for score in scores:
            self.score_distribution.observe(score)
```

### 2.4. Reproducibility (재현가능성) 구현

#### 환경 상태 관리
```python
import os
import json
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class EnvironmentSnapshot:
    """환경 스냅샷"""
    timestamp: str
    python_version: str
    package_versions: Dict[str, str]
    environment_variables: Dict[str, str]
    model_versions: Dict[str, str]
    random_seed: int
    
class ReproducibilityManager:
    """재현가능성 관리자"""
    
    def __init__(self):
        self.current_snapshot = None
    
    def capture_environment(self) -> EnvironmentSnapshot:
        """현재 환경 상태 캡처"""
        import sys
        import pkg_resources
        from datetime import datetime
        
        # 패키지 버전 수집
        package_versions = {
            pkg.project_name: pkg.version 
            for pkg in pkg_resources.working_set
        }
        
        # 환경 변수 수집 (민감한 정보 제외)
        safe_env_vars = {
            k: v for k, v in os.environ.items()
            if not any(sensitive in k.lower() for sensitive in ['password', 'key', 'secret', 'token'])
        }
        
        snapshot = EnvironmentSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            python_version=sys.version,
            package_versions=package_versions,
            environment_variables=safe_env_vars,
            model_versions=self._get_model_versions(),
            random_seed=42  # 고정 시드
        )
        
        self.current_snapshot = snapshot
        return snapshot
    
    def restore_environment(self, snapshot: EnvironmentSnapshot):
        """환경 상태 복원"""
        import random
        import numpy as np
        
        # 랜덤 시드 복원
        random.seed(snapshot.random_seed)
        np.random.seed(snapshot.random_seed)
        
        # 환경 변수 복원
        for key, value in snapshot.environment_variables.items():
            os.environ[key] = value
    
    def save_execution_context(self, input_data: Dict[str, Any], 
                             result: Any, execution_id: str):
        """실행 컨텍스트 저장"""
        context = {
            "execution_id": execution_id,
            "environment_snapshot": self.current_snapshot.__dict__,
            "input_data": input_data,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 실행 컨텍스트를 파일로 저장
        with open(f"execution_contexts/{execution_id}.json", "w") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
```

### 2.5. Explainability (설명가능성) 구현

#### 설명 생성 엔진
```python
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ExplanationComponent:
    """설명 구성요소"""
    factor: str
    weight: float
    contribution: float
    evidence: str
    confidence: float

class ExplanationGenerator:
    """설명 생성기"""
    
    def __init__(self):
        self.explanation_templates = {
            "high_relevance": "이 정책은 귀하의 {factor}와 {match_percentage:.1%} 일치하여 높은 관련성을 보입니다.",
            "eligibility_match": "귀하는 다음 자격 요건을 충족합니다: {requirements}",
            "score_breakdown": "총 점수 {total_score:.2f}는 다음과 같이 계산되었습니다: {breakdown}",
            "comparison": "이 정책은 다른 유사한 정책들보다 {advantage}에서 우수합니다."
        }
    
    def generate_explanation(self, recommendation: Dict[str, Any], 
                           user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """포괄적 설명 생성"""
        
        # 점수 분해 분석
        score_breakdown = self._analyze_score_breakdown(recommendation)
        
        # 자격 요건 매칭 분석
        eligibility_analysis = self._analyze_eligibility_match(
            recommendation, user_profile
        )
        
        # 비교 분석
        comparative_analysis = self._generate_comparative_analysis(recommendation)
        
        # 증거 수집
        evidence = self._collect_evidence(recommendation, user_profile)
        
        # 설명 구성
        explanation = {
            "summary": self._generate_summary(recommendation, user_profile),
            "score_breakdown": score_breakdown,
            "eligibility_match": eligibility_analysis,
            "comparative_advantages": comparative_analysis,
            "supporting_evidence": evidence,
            "confidence_level": self._calculate_explanation_confidence(recommendation),
            "limitations": self._identify_limitations(recommendation)
        }
        
        return explanation
    
    def _analyze_score_breakdown(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """점수 분해 분석"""
        score_components = recommendation.get("score_components", {})
        
        breakdown = {
            "total_score": recommendation.get("relevance_score", 0.0),
            "components": []
        }
        
        for component, score in score_components.items():
            breakdown["components"].append({
                "name": component,
                "score": score,
                "weight": score_components.get(f"{component}_weight", 1.0),
                "explanation": self._explain_component(component, score)
            })
        
        return breakdown
    
    def _generate_natural_language_explanation(self, explanation_data: Dict[str, Any]) -> str:
        """자연어 설명 생성"""
        parts = []
        
        # 요약 설명
        parts.append(explanation_data["summary"])
        
        # 점수 설명
        score_breakdown = explanation_data["score_breakdown"]
        parts.append(f"전체 점수 {score_breakdown['total_score']:.2f}점은 다음과 같이 구성됩니다:")
        
        for component in score_breakdown["components"]:
            parts.append(f"- {component['name']}: {component['score']:.2f}점 ({component['explanation']})")
        
        # 자격 요건 설명
        eligibility = explanation_data["eligibility_match"]
        if eligibility["matched_requirements"]:
            parts.append("귀하가 충족하는 자격 요건:")
            for req in eligibility["matched_requirements"]:
                parts.append(f"✓ {req}")
        
        return "\n".join(parts)
```

## 3. S.C.O.R.E. 메트릭 대시보드

### 3.1. 실시간 모니터링 대시보드
```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import json

class SCOREDashboard:
    """S.C.O.R.E. 메트릭 대시보드"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.metrics_collector = SCOREMetricsCollector()
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.get("/dashboard/score", response_class=HTMLResponse)
        async def score_dashboard():
            metrics = await self.metrics_collector.get_current_metrics()
            return self._render_dashboard(metrics)
        
        @self.app.get("/api/score/metrics")
        async def get_score_metrics():
            return await self.metrics_collector.get_current_metrics()
    
    def _render_dashboard(self, metrics: Dict[str, Any]) -> str:
        """대시보드 HTML 렌더링"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>S.C.O.R.E. Framework Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>S.C.O.R.E. Framework Metrics</h1>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Specificity</h3>
                    <div class="metric-value">{metrics['specificity']['score']:.2%}</div>
                    <div class="metric-details">
                        Schema Compliance: {metrics['specificity']['schema_compliance']:.2%}<br>
                        Field Completeness: {metrics['specificity']['field_completeness']:.2%}
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Consistency</h3>
                    <div class="metric-value">{metrics['consistency']['score']:.2%}</div>
                    <div class="metric-details">
                        Reproducibility: {metrics['consistency']['reproducibility']:.2%}<br>
                        Variance: {metrics['consistency']['variance']:.4f}
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Observability</h3>
                    <div class="metric-value">{metrics['observability']['score']:.2%}</div>
                    <div class="metric-details">
                        Log Coverage: {metrics['observability']['log_coverage']:.2%}<br>
                        Trace Completeness: {metrics['observability']['trace_completeness']:.2%}
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Reproducibility</h3>
                    <div class="metric-value">{metrics['reproducibility']['score']:.2%}</div>
                    <div class="metric-details">
                        Environment Consistency: {metrics['reproducibility']['env_consistency']:.2%}<br>
                        Result Stability: {metrics['reproducibility']['result_stability']:.2%}
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Explainability</h3>
                    <div class="metric-value">{metrics['explainability']['score']:.2%}</div>
                    <div class="metric-details">
                        Explanation Completeness: {metrics['explainability']['completeness']:.2%}<br>
                        User Understanding: {metrics['explainability']['user_understanding']:.2%}
                    </div>
                </div>
            </div>
            
            <div id="score-trend-chart"></div>
            
            <script>
                // 차트 렌더링 코드
                const trendData = {json.dumps(metrics['trend_data'])};
                Plotly.newPlot('score-trend-chart', trendData);
            </script>
        </body>
        </html>
        """

class SCOREMetricsCollector:
    """S.C.O.R.E. 메트릭 수집기"""
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """현재 S.C.O.R.E. 메트릭 수집"""
        return {
            "specificity": await self._collect_specificity_metrics(),
            "consistency": await self._collect_consistency_metrics(),
            "observability": await self._collect_observability_metrics(),
            "reproducibility": await self._collect_reproducibility_metrics(),
            "explainability": await self._collect_explainability_metrics(),
            "overall_score": await self._calculate_overall_score(),
            "trend_data": await self._get_trend_data()
        }
```

## 4. S.C.O.R.E. 품질 게이트

### 4.1. 자동화된 품질 검증
```python
class SCOREQualityGate:
    """S.C.O.R.E. 품질 게이트"""
    
    def __init__(self):
        self.thresholds = {
            "specificity": 0.95,
            "consistency": 0.90,
            "observability": 0.85,
            "reproducibility": 0.90,
            "explainability": 0.80
        }
    
    async def validate_deployment(self, service_name: str) -> Dict[str, Any]:
        """배포 전 S.C.O.R.E. 검증"""
        metrics = await self._collect_service_metrics(service_name)
        
        validation_results = {
            "service": service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "passed": True,
            "results": {}
        }
        
        for metric, threshold in self.thresholds.items():
            score = metrics.get(metric, {}).get("score", 0.0)
            passed = score >= threshold
            
            validation_results["results"][metric] = {
                "score": score,
                "threshold": threshold,
                "passed": passed,
                "details": metrics.get(metric, {})
            }
            
            if not passed:
                validation_results["passed"] = False
        
        return validation_results
    
    async def continuous_monitoring(self, service_name: str):
        """지속적 S.C.O.R.E. 모니터링"""
        while True:
            try:
                validation_result = await self.validate_deployment(service_name)
                
                if not validation_result["passed"]:
                    await self._trigger_alert(service_name, validation_result)
                
                await asyncio.sleep(300)  # 5분마다 검증
                
            except Exception as e:
                logger.error(f"S.C.O.R.E. monitoring error: {e}")
                await asyncio.sleep(60)
```

---

**📋 관련 문서**
- [Interactive AI Core](./02_INTERACTIVE_AI_CORE.md)
- [Living Gateway](./03_LIVING_GATEWAY.md)
- [Rule Engine](./04_RULE_ENGINE.md)
- [API 명세서](../03_DATA_AND_APIS/02_API_CONTRACT.md)