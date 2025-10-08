# 사용자 서비스 명세서 (User Service Specification)

| 항목 | 내용 |
|------|------|
| 문서 ID | AAS-USR-20250917-1.0 |
| 버전 | 1.0 |
| 최종 수정일 | 2025년 9월 17일 |
| 상태 | 확정 (Finalized) |

## 1. 서비스 개요 (Service Overview)

사용자 서비스는 이지스 시스템의 사용자 관리 및 인증을 담당하는 핵심 서비스이다. 본 서비스는 사용자 등록, 인증, 프로필 관리, 권한 제어를 통해 시스템의 보안과 개인화를 보장하며, 추천 서비스가 효과적인 맞춤형 서비스를 제공할 수 있도록 풍부한 사용자 컨텍스트를 제공한다.

### 1.1. 핵심 책임 (Core Responsibilities)
- 사용자 등록 및 이메일 인증
- JWT 기반 인증 및 세션 관리
- 사용자 프로필 관리 및 검증
- 역할 기반 접근 제어 (RBAC)
- 사용자 활동 추적 및 분석

### 1.2. 서비스 경계 (Service Boundaries)
**포함하는 기능:**
- 사용자 계정 생명주기 관리
- 인증 토큰 발급 및 검증
- 사용자 프로필 CRUD 연산
- 권한 및 역할 관리
- 사용자 활동 로깅

**포함하지 않는 기능:**
- 정책 추천 로직 (Recommendation Service 담당)
- 정책 데이터 관리 (Policy Service 담당)
- 비즈니스 규칙 처리 (Rule Engine 담당)

## 2. 아키텍처 설계 (Architecture Design)

### 2.1. 서비스 구조
```
┌─────────────────────────────────────────────────────────────┐
│                     User Service                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Auth Manager    │  │ Profile Manager │  │ Role Manager │ │
│  │                 │  │                 │  │              │ │
│  │ - Registration  │  │ - Profile CRUD  │  │ - RBAC       │ │
│  │ - Login/Logout  │  │ - Validation    │  │ - Permissions│ │
│  │ - Token Mgmt    │  │ - Preferences   │  │ - Audit      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Session Manager │  │ Activity Tracker│  │ Cache Layer  │ │
│  │                 │  │                 │  │              │ │
│  │ - Session Store │  │ - User Actions  │  │ - Sessions   │ │
│  │ - Timeout Mgmt  │  │ - Analytics     │  │ - Profiles   │ │
│  │ - Multi-device  │  │ - Behavior Log  │  │ - Permissions│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. 데이터 흐름 (Data Flow)
```
[Client] → [Auth Manager] → [JWT Token] → [Session Manager] → [Redis Cache]
    ↓           ↓              ↓              ↓                  ↓
[Registration] → [Profile Manager] → [Validation] → [PostgreSQL] → [Event Stream]
    ↓           ↓              ↓              ↓                  ↓
[User Actions] → [Activity Tracker] → [Analytics] → [Metrics] → [Monitoring]
```

## 3. 핵심 컴포넌트 상세 (Core Components)

### 3.1. Auth Manager (인증 관리자)
사용자 인증 및 토큰 관리를 담당한다.

**주요 기능:**
- **회원가입**: 이메일 중복 검사, 비밀번호 해싱, 이메일 인증
- **로그인**: 자격 증명 검증, JWT 토큰 발급
- **토큰 관리**: 토큰 갱신, 무효화, 만료 처리

```python
class AuthManager:
    def __init__(self, db: Database, email_service: EmailService, cache: Cache):
        self.db = db
        self.email_service = email_service
        self.cache = cache
        self.password_hasher = PasswordHasher()
        self.jwt_handler = JWTHandler()
    
    async def register_user(self, registration_data: UserRegistration) -> UserRegistrationResult:
        """사용자 등록"""
        # 1. 이메일 중복 검사
        existing_user = await self.db.get_user_by_email(registration_data.email)
        if existing_user:
            raise EmailAlreadyExistsError(registration_data.email)
        
        # 2. 비밀번호 해싱
        hashed_password = await self.password_hasher.hash(registration_data.password)
        
        # 3. 사용자 생성
        user = User(
            user_id=uuid4(),
            email=registration_data.email,
            hashed_password=hashed_password,
            profile=registration_data.profile,
            is_active=True,
            email_verified=False,
            created_at=datetime.utcnow()
        )
        
        await self.db.save_user(user)
        
        # 4. 이메일 인증 토큰 생성 및 발송
        verification_token = self._generate_verification_token(user.user_id)
        await self.email_service.send_verification_email(
            user.email, 
            verification_token
        )
        
        return UserRegistrationResult(
            user_id=user.user_id,
            email=user.email,
            verification_required=True
        )
    
    async def authenticate_user(self, credentials: LoginCredentials) -> AuthenticationResult:
        """사용자 인증"""
        # 1. 사용자 조회
        user = await self.db.get_user_by_email(credentials.email)
        if not user or not user.is_active:
            raise InvalidCredentialsError()
        
        # 2. 비밀번호 검증
        is_valid = await self.password_hasher.verify(
            credentials.password, 
            user.hashed_password
        )
        if not is_valid:
            raise InvalidCredentialsError()
        
        # 3. 이메일 인증 확인
        if not user.email_verified:
            raise EmailNotVerifiedError()
        
        # 4. JWT 토큰 생성
        access_token = self.jwt_handler.create_access_token(
            user_id=user.user_id,
            email=user.email,
            roles=user.roles
        )
        
        refresh_token = self.jwt_handler.create_refresh_token(user.user_id)
        
        # 5. 세션 생성
        session = await self.session_manager.create_session(
            user_id=user.user_id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        # 6. 로그인 기록
        await self.activity_tracker.log_login(user.user_id)
        
        return AuthenticationResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=3600,
            user=UserInfo.from_user(user)
        )
```

### 3.2. Profile Manager (프로필 관리자)
사용자 프로필 정보를 관리한다.

**프로필 구조:**
```python
class UserProfile(BaseModel):
    business_info: BusinessInfo
    location: LocationInfo
    financial_info: Optional[FinancialInfo] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)

class BusinessInfo(BaseModel):
    business_type: BusinessType
    industry_code: str = Field(..., regex=r'^\d{2,5}$')
    industry_name: str
    business_scale: Optional[str] = None
    establishment_date: Optional[date] = None
    employee_count: Optional[int] = Field(None, ge=0, le=10000)
    business_registration_number: Optional[str] = None  # 해시된 값

class LocationInfo(BaseModel):
    region_code: str = Field(..., regex=r'^\d{2}$')
    region_name: str
    detailed_address: Optional[str] = None  # 암호화된 값

class FinancialInfo(BaseModel):
    annual_revenue: Optional[int] = Field(None, ge=0)
    current_funding: List[str] = Field(default_factory=list)  # 기존 수혜 정책 ID들
    credit_rating: Optional[str] = None

class UserPreferences(BaseModel):
    funding_purposes: List[str] = Field(default_factory=list)
    preferred_amount_range: Optional[Tuple[int, int]] = None
    max_interest_rate: Optional[float] = Field(None, ge=0, le=100)
    notification_settings: NotificationSettings = Field(default_factory=NotificationSettings)
```

**프로필 검증:**
```python
class ProfileManager:
    async def update_profile(self, user_id: UUID, profile_update: ProfileUpdate) -> UserProfile:
        """사용자 프로필 업데이트"""
        # 1. 사용자 존재 확인
        user = await self.db.get_user(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        
        # 2. 프로필 검증
        validation_result = await self.validator.validate_profile(profile_update)
        if not validation_result.is_valid:
            raise ProfileValidationError(validation_result.errors)
        
        # 3. 민감 정보 처리
        processed_profile = await self._process_sensitive_data(profile_update)
        
        # 4. 프로필 업데이트
        user.profile = {**user.profile, **processed_profile.dict(exclude_unset=True)}
        user.updated_at = datetime.utcnow()
        
        await self.db.save_user(user)
        
        # 5. 프로필 변경 이벤트 발행
        await self.event_publisher.publish(ProfileUpdatedEvent(
            user_id=user_id,
            changes=profile_update.dict(exclude_unset=True)
        ))
        
        return UserProfile(**user.profile)
    
    async def _process_sensitive_data(self, profile: ProfileUpdate) -> ProfileUpdate:
        """민감한 개인정보 처리"""
        if profile.business_info and profile.business_info.business_registration_number:
            # 사업자등록번호 해싱
            profile.business_info.business_registration_number = self.hasher.hash(
                profile.business_info.business_registration_number
            )
        
        if profile.location and profile.location.detailed_address:
            # 상세 주소 암호화
            profile.location.detailed_address = self.encryptor.encrypt(
                profile.location.detailed_address
            )
        
        return profile
```

### 3.3. Role Manager (역할 관리자)
역할 기반 접근 제어를 구현한다.

**역할 정의:**
```python
class Role(str, Enum):
    USER = "user"           # 일반 사용자
    PREMIUM_USER = "premium_user"  # 프리미엄 사용자
    ADMIN = "admin"         # 관리자
    SUPER_ADMIN = "super_admin"    # 최고 관리자

class Permission(str, Enum):
    READ_POLICIES = "read:policies"
    GET_RECOMMENDATIONS = "get:recommendations"
    MANAGE_PROFILE = "manage:profile"
    ADMIN_POLICIES = "admin:policies"
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"

# 역할별 권한 매핑
ROLE_PERMISSIONS = {
    Role.USER: [
        Permission.READ_POLICIES,
        Permission.GET_RECOMMENDATIONS,
        Permission.MANAGE_PROFILE
    ],
    Role.PREMIUM_USER: [
        Permission.READ_POLICIES,
        Permission.GET_RECOMMENDATIONS,
        Permission.MANAGE_PROFILE,
        # 추가 프리미엄 기능들
    ],
    Role.ADMIN: [
        Permission.READ_POLICIES,
        Permission.GET_RECOMMENDATIONS,
        Permission.MANAGE_PROFILE,
        Permission.ADMIN_POLICIES,
        Permission.ADMIN_USERS
    ],
    Role.SUPER_ADMIN: list(Permission)  # 모든 권한
}
```

## 4. API 명세 (API Specification)

### 4.1. 인증 관련 API

#### POST /auth/signup
```json
{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "profile": {
        "business_info": {
            "business_type": "소상공인",
            "industry_code": "56",
            "industry_name": "음식점업"
        },
        "location": {
            "region_code": "11",
            "region_name": "서울특별시"
        }
    }
}
```

#### POST /auth/login
```json
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}
```

#### POST /auth/refresh
```json
{
    "refresh_token": "refresh_token_string"
}
```

#### POST /auth/logout
```http
Authorization: Bearer {access_token}
```

### 4.2. 프로필 관리 API

#### GET /users/profile
```http
Authorization: Bearer {access_token}
```

#### PUT /users/profile
```json
{
    "business_info": {
        "employee_count": 5,
        "annual_revenue": 80000000
    },
    "preferences": {
        "funding_purposes": ["운영자금", "시설자금"],
        "max_interest_rate": 5.0
    }
}
```

#### DELETE /users/account
```http
Authorization: Bearer {access_token}
```

## 5. 보안 구현 (Security Implementation)

### 5.1. 비밀번호 보안
```python
class PasswordHasher:
    def __init__(self):
        self.hasher = argon2.PasswordHasher(
            time_cost=3,      # 반복 횟수
            memory_cost=65536, # 메모리 사용량 (64MB)
            parallelism=1,    # 병렬 처리 수
            hash_len=32,      # 해시 길이
            salt_len=16       # 솔트 길이
        )
    
    async def hash(self, password: str) -> str:
        """비밀번호 해싱"""
        # 비밀번호 강도 검사
        if not self._is_strong_password(password):
            raise WeakPasswordError()
        
        return self.hasher.hash(password)
    
    async def verify(self, password: str, hashed: str) -> bool:
        """비밀번호 검증"""
        try:
            self.hasher.verify(hashed, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
    
    def _is_strong_password(self, password: str) -> bool:
        """비밀번호 강도 검사"""
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return sum([has_upper, has_lower, has_digit, has_special]) >= 3
```

### 5.2. JWT 토큰 관리
```python
class JWTHandler:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=30)
    
    def create_access_token(self, user_id: UUID, email: str, roles: List[str]) -> str:
        """액세스 토큰 생성"""
        payload = {
            "sub": str(user_id),
            "email": email,
            "roles": roles,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.access_token_expire
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: UUID) -> str:
        """리프레시 토큰 생성"""
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.refresh_token_expire
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """토큰 검증"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError:
            raise InvalidTokenError()
```

## 6. 성능 요구사항 (Performance Requirements)

### 6.1. 응답 시간 목표
- **로그인**: 500ms 이내
- **프로필 조회**: 200ms 이내
- **프로필 업데이트**: 1초 이내
- **토큰 검증**: 50ms 이내

### 6.2. 처리량 목표
- **동시 로그인**: 1,000 TPS
- **토큰 검증**: 10,000 TPS
- **프로필 조회**: 5,000 TPS

### 6.3. 가용성 목표
- **서비스 가용성**: 99.9%
- **인증 성공률**: 99.95%

## 7. 모니터링 및 메트릭 (Monitoring & Metrics)

### 7.1. 인증 메트릭
```python
# 인증 관련 메트릭
login_attempts = Counter('user_login_attempts_total', ['status'])
login_duration = Histogram('user_login_duration_seconds')
active_sessions = Gauge('active_user_sessions')
token_validations = Counter('jwt_token_validations_total', ['status'])

# 사용자 활동 메트릭
user_registrations = Counter('user_registrations_total')
profile_updates = Counter('user_profile_updates_total')
password_resets = Counter('password_reset_requests_total')
```

### 7.2. 보안 메트릭
```python
# 보안 관련 메트릭
failed_login_attempts = Counter('failed_login_attempts_total', ['reason'])
suspicious_activities = Counter('suspicious_user_activities_total', ['type'])
account_lockouts = Counter('account_lockouts_total')
```

## 8. 에러 처리 (Error Handling)

### 8.1. 에러 분류
```python
class UserServiceError(Exception):
    pass

class AuthenticationError(UserServiceError):
    pass

class EmailAlreadyExistsError(AuthenticationError):
    pass

class InvalidCredentialsError(AuthenticationError):
    pass

class EmailNotVerifiedError(AuthenticationError):
    pass

class TokenExpiredError(AuthenticationError):
    pass

class ProfileValidationError(UserServiceError):
    pass

class UserNotFoundError(UserServiceError):
    pass
```

### 8.2. 에러 응답 형식
```json
{
    "success": false,
    "error": {
        "code": "EMAIL_ALREADY_EXISTS",
        "message": "이미 등록된 이메일 주소입니다.",
        "details": {
            "email": "user@example.com",
            "suggestion": "다른 이메일 주소를 사용하거나 로그인을 시도해주세요."
        }
    }
}
```

---

**📋 관련 문서**
- [API 명세서](../../03_DATA_MODELS_AND_APIS/API_CONTRACT.md)
- [데이터베이스 스키마](../../03_DATA_MODELS_AND_APIS/DATABASE_SCHEMA.md)
- [보안 정책](../../05_OPERATIONS/04_SECURITY_POLICY.md)