# 이지스(Aegis) API 규약 명세서

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-API-20250917-1.0 |
| 작성자 | Dr. Aiden (수석 AI 시스템 아키텍트) |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 '이지스(Aegis)' 시스템의 모든 API(Application Programming Interface) 엔드포인트, 요청/응답 형식, 인증 방식 등을 정의하는 공식 규약이다. 모든 클라이언트-서버 및 서버-서버 간 통신은 본 문서의 명세를 따라야 한다. 본 규약은 **OpenAPI 3.0** 표준을 준수하여 명확성과 도구 호환성을 보장한다.

## 2. 공통 규약 (General Contracts)

### 2.1. 기본 설정
- **Base URL**: `https://api.aegis.kr/api/v1`
- **Content-Type**: `application/json`
- **Character Encoding**: `UTF-8`
- **API 버전 관리**: URL 경로에 버전 포함 (`/api/v1/`)

### 2.2. 인증 (Authentication)
모든 API 요청은 `Authorization` 헤더에 Bearer JWT 토큰을 포함해야 한다. (로그인/회원가입 엔드포인트 제외)

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2.3. 표준 응답 형식

#### 성공 응답
```json
{
  "success": true,
  "data": { /* 실제 데이터 */ },
  "metadata": {
    "timestamp": "2025-09-17T10:30:00Z",
    "request_id": "req_123456789",
    "processing_time_ms": 245
  }
}
```

#### 에러 응답
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "해당 정책 정보를 찾을 수 없습니다.",
    "details": {
      "policy_id": "invalid-uuid",
      "suggestion": "정책 ID를 확인해주세요."
    }
  },
  "metadata": {
    "timestamp": "2025-09-17T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### 2.4. HTTP 상태 코드
| 코드 | 의미 | 사용 상황 |
|------|------|-----------|
| 200 | OK | 성공적인 요청 처리 |
| 201 | Created | 리소스 생성 성공 |
| 400 | Bad Request | 잘못된 요청 형식 |
| 401 | Unauthorized | 인증 실패 |
| 403 | Forbidden | 권한 부족 |
| 404 | Not Found | 리소스 없음 |
| 429 | Too Many Requests | 요청 한도 초과 |
| 500 | Internal Server Error | 서버 내부 오류 |
| 503 | Service Unavailable | 서비스 일시 불가 |

## 3. 핵심 API: 정책자금 추천 시스템

### 3.1. 정책자금 검색 및 추천

#### POST /recommendations
사용자의 자연어 질문과 프로필을 기반으로 맞춤형 정책자금 목록을 반환한다.

**Request Body:**
```json
{
  "session_id": "user123-sess456",
  "query": "경기도에서 카페를 막 창업했는데, 운영 자금이 부족합니다. 지원받을 수 있는 정책이 있을까요?",
  "user_profile": {
    "business_info": {
      "business_type": "소상공인",
      "industry_code": "56",
      "industry_name": "음식점업",
      "establishment_date": "2025-06-15",
      "employee_count": 2
    },
    "location": {
      "region_code": "41",
      "region_name": "경기도 성남시"
    },
    "financial_info": {
      "annual_revenue": 50000000,
      "funding_purpose": ["운영자금"]
    }
  },
  "search_options": {
    "max_results": 10,
    "include_expired": false,
    "sort_by": "relevance"
  }
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "rank": 1,
        "policy": {
          "policy_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "title": "경기도 소상공인 특별경영자금",
          "issuing_organization": "경기도청",
          "summary": "경기도 내 소상공인의 경영 안정을 위해 저금리로 운영 자금을 지원하는 정책입니다.",
          "funding_details": {
            "max_amount": 50000000,
            "interest_rate": 2.5,
            "repayment_period": "5년"
          },
          "application_period": {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31"
          },
          "url": "https://www.gg.go.kr/policy/123"
        },
        "score_breakdown": {
          "final_score": 0.95,
          "semantic_similarity": 0.88,
          "kg_boost_factor": 1.08,
          "rule_adjustments": 0.02,
          "matched_rules": ["rule_startup_boost", "rule_region_match"]
        },
        "explanation": {
          "why_recommended": "귀하의 업종(음식점업)과 지역(경기도), 그리고 창업 초기 단계에 가장 적합한 정책입니다.",
          "evidence_snippet": "경기도에 사업장을 둔 창업 1년 미만 소상공인을 대상으로 운영자금을 지원합니다.",
          "eligibility_match": {
            "region": "✓ 경기도 소재",
            "business_type": "✓ 소상공인",
            "industry": "✓ 음식점업 포함",
            "startup_age": "✓ 창업 1년 미만"
          }
        }
      }
    ],
    "search_metadata": {
      "total_policies_searched": 1247,
      "vector_search_time_ms": 45,
      "kg_reasoning_time_ms": 123,
      "total_processing_time_ms": 245,
      "search_strategy": "hybrid_rag_kg"
    }
  },
  "metadata": {
    "timestamp": "2025-09-17T10:30:00Z",
    "request_id": "req_rec_123456789",
    "processing_time_ms": 245
  }
}
```

#### GET /recommendations/{recommendation_id}
이전 추천 결과를 조회한다.

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "recommendation_id": "rec_123456789",
    "created_at": "2025-09-17T10:30:00Z",
    "query": "원본 쿼리",
    "recommendations": [ /* 추천 결과 배열 */ ],
    "user_feedback": {
      "helpful_policies": ["policy_id_1"],
      "not_helpful_policies": ["policy_id_2"],
      "overall_rating": 4
    }
  }
}
```

### 3.2. 정책 상세 조회

#### GET /policies/{policy_id}
특정 정책의 상세 정보를 조회한다.

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "policy_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "경기도 소상공인 특별경영자금",
    "issuing_organization": "경기도청",
    "description": "상세 설명...",
    "eligibility_criteria": [
      "경기도 내 사업장 보유",
      "소상공인 기준 충족",
      "업력 1년 이상"
    ],
    "funding_details": {
      "funding_type": "대출",
      "max_amount": 50000000,
      "min_amount": 5000000,
      "interest_rate": 2.5,
      "repayment_period": "최대 5년",
      "guarantee_required": true
    },
    "application_info": {
      "application_method": "온라인 신청",
      "required_documents": [
        "사업자등록증",
        "재무제표",
        "사업계획서"
      ],
      "processing_time": "2-3주",
      "contact_info": {
        "phone": "031-120",
        "website": "https://www.gg.go.kr"
      }
    },
    "related_policies": [
      {
        "policy_id": "related_policy_1",
        "title": "관련 정책 1",
        "relationship": "complementary"
      }
    ]
  }
}
```

#### GET /policies/search
키워드 기반 정책 검색 (간단한 검색용)

**Query Parameters:**
- `q`: 검색 키워드
- `region`: 지역 필터
- `industry`: 업종 필터
- `limit`: 결과 수 제한 (기본값: 20)
- `offset`: 페이지네이션 오프셋

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "policies": [ /* 정책 목록 */ ],
    "pagination": {
      "total": 156,
      "limit": 20,
      "offset": 0,
      "has_next": true
    }
  }
}
```

## 4. 사용자 관리 API

### 4.1. 인증 관련

#### POST /auth/signup
회원가입

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123!",
  "profile": {
    "business_info": {
      "business_type": "소상공인",
      "industry_name": "음식점업"
    },
    "location": {
      "region_name": "서울특별시 강남구"
    }
  }
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123456789",
    "email": "user@example.com",
    "email_verification_required": true
  }
}
```

#### POST /auth/login
로그인

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123!"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "refresh_token_string",
    "user": {
      "user_id": "user_123456789",
      "email": "user@example.com"
    }
  }
}
```

#### POST /auth/refresh
토큰 갱신

**Request Body:**
```json
{
  "refresh_token": "refresh_token_string"
}
```

### 4.2. 사용자 프로필 관리

#### GET /users/profile
현재 사용자 프로필 조회

#### PUT /users/profile
사용자 프로필 업데이트

**Request Body:**
```json
{
  "business_info": {
    "business_type": "소상공인",
    "industry_code": "56",
    "industry_name": "음식점업",
    "establishment_date": "2025-06-15",
    "employee_count": 3
  },
  "location": {
    "region_code": "11",
    "region_name": "서울특별시 강남구"
  },
  "financial_info": {
    "annual_revenue": 80000000,
    "funding_purpose": ["운영자금", "시설자금"]
  }
}
```

## 5. 피드백 및 분석 API

### 5.1. 사용자 피드백

#### POST /recommendations/{recommendation_id}/feedback
추천 결과에 대한 피드백 제공

**Request Body:**
```json
{
  "overall_rating": 4,
  "helpful_policies": ["policy_id_1", "policy_id_2"],
  "not_helpful_policies": ["policy_id_3"],
  "comments": "추천이 정확했습니다. 특히 첫 번째 정책이 도움이 되었어요.",
  "applied_policies": ["policy_id_1"]
}
```

#### GET /users/recommendations/history
사용자의 추천 이력 조회

## 6. 관리자 API (Admin)

### 6.1. 시스템 모니터링

#### GET /admin/health
시스템 상태 확인

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "services": {
      "database": "healthy",
      "vector_db": "healthy",
      "graph_db": "healthy",
      "cache": "healthy",
      "llm_gateway": "healthy"
    },
    "metrics": {
      "active_users": 1247,
      "total_policies": 3456,
      "avg_response_time_ms": 245
    }
  }
}
```

#### GET /admin/metrics
시스템 메트릭 조회

## 7. 에러 코드 정의

| 에러 코드 | HTTP 상태 | 설명 |
|-----------|-----------|------|
| `INVALID_REQUEST_FORMAT` | 400 | 요청 형식이 올바르지 않음 |
| `MISSING_REQUIRED_FIELD` | 400 | 필수 필드 누락 |
| `INVALID_CREDENTIALS` | 401 | 잘못된 인증 정보 |
| `TOKEN_EXPIRED` | 401 | 토큰 만료 |
| `INSUFFICIENT_PERMISSIONS` | 403 | 권한 부족 |
| `RESOURCE_NOT_FOUND` | 404 | 리소스를 찾을 수 없음 |
| `POLICY_NOT_FOUND` | 404 | 정책을 찾을 수 없음 |
| `USER_NOT_FOUND` | 404 | 사용자를 찾을 수 없음 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 한도 초과 |
| `LLM_SERVICE_UNAVAILABLE` | 503 | LLM 서비스 일시 불가 |
| `DATABASE_CONNECTION_ERROR` | 503 | 데이터베이스 연결 오류 |

## 8. 요청 제한 (Rate Limiting)

| 엔드포인트 | 제한 | 윈도우 |
|------------|------|--------|
| `/recommendations` | 100 요청 | 1시간 |
| `/auth/login` | 5 요청 | 15분 |
| `/policies/search` | 1000 요청 | 1시간 |
| 기타 API | 1000 요청 | 1시간 |

## 9. 웹훅 (Webhooks)

### 9.1. 정책 업데이트 알림
새로운 정책이 추가되거나 기존 정책이 변경될 때 등록된 웹훅으로 알림을 전송한다.

**Webhook Payload:**
```json
{
  "event_type": "policy.created",
  "timestamp": "2025-09-17T10:30:00Z",
  "data": {
    "policy_id": "new_policy_123",
    "title": "새로운 정책명",
    "changes": ["created"]
  }
}
```

---

**📋 관련 문서**
- [데이터베이스 스키마](./DATABASE_SCHEMA.md)
- [시스템 아키텍처](../01_SYSTEM_ARCHITECTURE.md)
- [구현 계획](../IMPLEMENTATION_PLAN.md)