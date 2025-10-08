# 사용자 서비스 API 명세서

| 항목 | 내용 |
|------|------|
| 문서 ID | AEG-SPC-USER-20250917-4.0 |
| 버전 | 4.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 작성자 | Dr. Aiden (수석 AI 시스템 아키텍트) |
| 상태 | 확정 (Finalized) |

## 1. 개요 (Overview)

본 문서는 이지스 시스템의 사용자 서비스 API에 대한 상세 명세를 정의한다. **RESTful API** 설계 원칙을 따르며, **OpenAPI 3.0** 표준을 준수한다.

## 2. API 기본 정보

### 2.1. 기본 설정
- **Base URL**: `https://api.aegis.kr/api/v1/users`
- **Content-Type**: `application/json`
- **Character Encoding**: `UTF-8`
- **Authentication**: Bearer JWT Token

### 2.2. 공통 응답 형식

#### 성공 응답
```json
{
  "success": true,
  "data": {
    // 실제 데이터
  },
  "metadata": {
    "timestamp": "2025-09-17T10:30:00Z",
    "request_id": "req_123456789",
    "version": "v1"
  }
}
```

#### 에러 응답
```json
{
  "success": false,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "사용자를 찾을 수 없습니다.",
    "details": {
      "user_id": "invalid-uuid",
      "suggestion": "사용자 ID를 확인해주세요."
    }
  },
  "metadata": {
    "timestamp": "2025-09-17T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

## 3. 인증 관련 API

### 3.1. 회원가입

#### POST /auth/register
사용자 회원가입을 처리한다.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "business_registration_number": "123-45-67890",
  "terms_agreed": true,
  "privacy_policy_agreed": true,
  "marketing_agreed": false
}
```

**Request Schema:**
```json
{
  "type": "object",
  "required": ["email", "password", "business_registration_number", "terms_agreed", "privacy_policy_agreed"],
  "properties": {
    "email": {
      "type": "string",
      "format": "email",
      "maxLength": 255,
      "description": "사용자 이메일 주소"
    },
    "password": {
      "type": "string",
      "minLength": 8,
      "maxLength": 128,
      "pattern": "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]",
      "description": "비밀번호 (최소 8자, 대소문자, 숫자, 특수문자 포함)"
    },
    "business_registration_number": {
      "type": "string",
      "pattern": "^\\d{3}-\\d{2}-\\d{5}$",
      "description": "사업자등록번호 (000-00-00000 형식)"
    },
    "terms_agreed": {
      "type": "boolean",
      "const": true,
      "description": "이용약관 동의 (필수)"
    },
    "privacy_policy_agreed": {
      "type": "boolean",
      "const": true,
      "description": "개인정보처리방침 동의 (필수)"
    },
    "marketing_agreed": {
      "type": "boolean",
      "description": "마케팅 정보 수신 동의 (선택)"
    }
  }
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "user_id": "usr_1234567890abcdef",
    "email": "user@example.com",
    "status": "pending_verification",
    "business_profile": {
      "business_name": "홍길동 카페",
      "business_type": "개인사업자",
      "industry_name": "음식점업"
    },
    "verification_email_sent": true
  },
  "metadata": {
    "timestamp": "2025-09-17T10:30:00Z",
    "request_id": "req_register_123"
  }
}
```

**Error Responses:**
- `400 Bad Request`: 잘못된 요청 데이터
- `409 Conflict`: 이미 존재하는 이메일 또는 사업자등록번호
- `422 Unprocessable Entity`: 사업자등록번호 검증 실패

### 3.2. 로그인

#### POST /auth/login
사용자 로그인을 처리한다.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "remember_me": false
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "user_id": "usr_1234567890abcdef",
      "email": "user@example.com",
      "status": "active",
      "last_login_at": "2025-09-17T10:30:00Z"
    }
  }
}
```

### 3.3. 토큰 갱신

#### POST /auth/refresh
리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급한다.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

### 3.4. 로그아웃

#### POST /auth/logout
사용자 로그아웃을 처리한다.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "성공적으로 로그아웃되었습니다."
  }
}
```

## 4. 사용자 프로필 관리 API

### 4.1. 프로필 조회

#### GET /profile
현재 사용자의 프로필 정보를 조회한다.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user_id": "usr_1234567890abcdef",
    "email": "user@example.com",
    "status": "active",
    "email_verified": true,
    "created_at": "2025-09-01T10:00:00Z",
    "business_profile": {
      "business_registration_number": "123-45-67890",
      "business_name": "홍길동 카페",
      "business_type": "개인사업자",
      "industry_code": "56211",
      "industry_name": "한식 음식점업",
      "establishment_date": "2024-01-15",
      "annual_revenue": 100000000,
      "employee_count": 3,
      "business_address": "서울특별시 강남구 테헤란로 123",
      "updated_at": "2025-09-15T14:30:00Z"
    },
    "preferences": {
      "preferred_funding_types": ["운영자금", "시설자금"],
      "max_interest_rate": 5.0,
      "preferred_amount_range": [10000000, 50000000],
      "complexity_tolerance": "medium",
      "notification_preferences": {
        "email_notifications": true,
        "sms_notifications": false,
        "push_notifications": true
      }
    }
  }
}
```

### 4.2. 프로필 업데이트

#### PUT /profile
사용자 프로필 정보를 업데이트한다.

**Request Body:**
```json
{
  "business_profile": {
    "annual_revenue": 120000000,
    "employee_count": 5,
    "business_address": "서울특별시 강남구 테헤란로 456"
  },
  "preferences": {
    "preferred_funding_types": ["운영자금", "시설자금", "마케팅자금"],
    "max_interest_rate": 4.5,
    "preferred_amount_range": [20000000, 80000000],
    "complexity_tolerance": "high"
  }
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "프로필이 성공적으로 업데이트되었습니다.",
    "updated_fields": [
      "business_profile.annual_revenue",
      "business_profile.employee_count",
      "business_profile.business_address",
      "preferences.preferred_funding_types",
      "preferences.max_interest_rate",
      "preferences.preferred_amount_range",
      "preferences.complexity_tolerance"
    ],
    "updated_at": "2025-09-17T10:30:00Z"
  }
}
```

### 4.3. 비밀번호 변경

#### PUT /profile/password
사용자 비밀번호를 변경한다.

**Request Body:**
```json
{
  "current_password": "CurrentPassword123!",
  "new_password": "NewSecurePassword456!",
  "confirm_password": "NewSecurePassword456!"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "비밀번호가 성공적으로 변경되었습니다.",
    "password_changed_at": "2025-09-17T10:30:00Z"
  }
}
```

## 5. 계정 관리 API

### 5.1. 이메일 인증

#### POST /auth/verify-email
이메일 인증을 처리한다.

**Request Body:**
```json
{
  "verification_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "이메일 인증이 완료되었습니다.",
    "user_status": "active",
    "verified_at": "2025-09-17T10:30:00Z"
  }
}
```

### 5.2. 비밀번호 재설정 요청

#### POST /auth/forgot-password
비밀번호 재설정 이메일을 발송한다.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "비밀번호 재설정 이메일이 발송되었습니다.",
    "email_sent_to": "u***@example.com"
  }
}
```

### 5.3. 비밀번호 재설정

#### POST /auth/reset-password
비밀번호를 재설정한다.

**Request Body:**
```json
{
  "reset_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "NewSecurePassword789!",
  "confirm_password": "NewSecurePassword789!"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "비밀번호가 성공적으로 재설정되었습니다.",
    "password_reset_at": "2025-09-17T10:30:00Z"
  }
}
```

## 6. 계정 설정 API

### 6.1. 알림 설정 조회

#### GET /settings/notifications
사용자의 알림 설정을 조회한다.

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "email_notifications": {
      "new_policy_alerts": true,
      "recommendation_updates": true,
      "account_security": true,
      "marketing": false
    },
    "sms_notifications": {
      "urgent_alerts": true,
      "deadline_reminders": false
    },
    "push_notifications": {
      "new_recommendations": true,
      "application_status": true
    }
  }
}
```

### 6.2. 알림 설정 업데이트

#### PUT /settings/notifications
사용자의 알림 설정을 업데이트한다.

**Request Body:**
```json
{
  "email_notifications": {
    "new_policy_alerts": false,
    "recommendation_updates": true,
    "account_security": true,
    "marketing": false
  },
  "sms_notifications": {
    "urgent_alerts": true,
    "deadline_reminders": true
  }
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "알림 설정이 업데이트되었습니다.",
    "updated_at": "2025-09-17T10:30:00Z"
  }
}
```

### 6.3. 계정 삭제

#### DELETE /profile
사용자 계정을 삭제한다.

**Request Body:**
```json
{
  "password": "CurrentPassword123!",
  "deletion_reason": "서비스 불만족",
  "confirm_deletion": true
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "계정이 성공적으로 삭제되었습니다.",
    "deletion_scheduled_at": "2025-09-24T10:30:00Z",
    "data_retention_period": "30일"
  }
}
```

## 7. 에러 코드 정의

| 에러 코드 | HTTP 상태 | 설명 |
|-----------|-----------|------|
| `INVALID_REQUEST_FORMAT` | 400 | 요청 형식이 올바르지 않음 |
| `MISSING_REQUIRED_FIELD` | 400 | 필수 필드 누락 |
| `INVALID_EMAIL_FORMAT` | 400 | 이메일 형식이 올바르지 않음 |
| `WEAK_PASSWORD` | 400 | 비밀번호가 보안 요구사항을 충족하지 않음 |
| `INVALID_CREDENTIALS` | 401 | 잘못된 인증 정보 |
| `TOKEN_EXPIRED` | 401 | 토큰 만료 |
| `TOKEN_INVALID` | 401 | 유효하지 않은 토큰 |
| `ACCOUNT_NOT_VERIFIED` | 403 | 이메일 인증이 완료되지 않음 |
| `ACCOUNT_SUSPENDED` | 403 | 계정이 정지됨 |
| `USER_NOT_FOUND` | 404 | 사용자를 찾을 수 없음 |
| `EMAIL_ALREADY_EXISTS` | 409 | 이미 존재하는 이메일 |
| `BUSINESS_REG_ALREADY_EXISTS` | 409 | 이미 등록된 사업자등록번호 |
| `INVALID_BUSINESS_REGISTRATION` | 422 | 유효하지 않은 사업자등록번호 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 한도 초과 |
| `INTERNAL_SERVER_ERROR` | 500 | 서버 내부 오류 |

## 8. 요청 제한 (Rate Limiting)

| 엔드포인트 | 제한 | 윈도우 |
|------------|------|--------|
| `POST /auth/login` | 5 요청 | 15분 |
| `POST /auth/register` | 3 요청 | 1시간 |
| `POST /auth/forgot-password` | 3 요청 | 1시간 |
| `PUT /profile` | 10 요청 | 1시간 |
| 기타 인증된 요청 | 1000 요청 | 1시간 |
| 기타 비인증 요청 | 100 요청 | 1시간 |

## 9. 보안 헤더

모든 API 응답에는 다음 보안 헤더가 포함된다:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

---

**📋 관련 문서**
- [기술 설계](./03_TECHNICAL_DESIGN.md)
- [데이터 모델](./05_DATA_MODEL.md)
- [테스트 전략](./08_TESTING_STRATEGY.md)
- [전체 API 명세](../../03_DATA_AND_APIS/02_API_CONTRACT.md)