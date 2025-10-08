"""
샘플 서비스 이벤트 핸들러
"""

from aegis_shared.messaging import EventSubscriber
from aegis_shared.logging import get_logger, add_context

logger = get_logger(__name__)


def setup_event_handlers(subscriber: EventSubscriber):
    """이벤트 핸들러 설정"""
    
    @subscriber.handler("user.created")
    async def handle_user_created(event):
        """사용자 생성 이벤트 처리"""
        user_data = event["data"]
        add_context(event_type="user.created", user_id=user_data["user_id"])
        
        logger.info(
            "Processing user created event",
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        
        # 비즈니스 로직 처리
        await send_welcome_email(user_data)
        await create_user_profile(user_data)
        await update_user_statistics()
        
        logger.info("User created event processed successfully")
    
    @subscriber.handler("user.updated")
    async def handle_user_updated(event):
        """사용자 업데이트 이벤트 처리"""
        user_data = event["data"]
        add_context(event_type="user.updated", user_id=user_data["user_id"])
        
        logger.info(
            "Processing user updated event",
            user_id=user_data["user_id"],
            changes=user_data.get("changes", {})
        )
        
        # 변경사항에 따른 처리
        changes = user_data.get("changes", {})
        
        if "email" in changes:
            await update_email_subscriptions(user_data["user_id"], changes["email"])
        
        if "name" in changes:
            await update_user_profile_name(user_data["user_id"], changes["name"])
        
        # 캐시 무효화
        await invalidate_user_cache(user_data["user_id"])
        
        logger.info("User updated event processed successfully")
    
    @subscriber.handler("user.deleted")
    async def handle_user_deleted(event):
        """사용자 삭제 이벤트 처리"""
        user_data = event["data"]
        add_context(event_type="user.deleted", user_id=user_data["user_id"])
        
        logger.info(
            "Processing user deleted event",
            user_id=user_data["user_id"]
        )
        
        # 관련 데이터 정리
        await cleanup_user_data(user_data["user_id"])
        await send_account_deletion_notification(user_data["user_id"])
        await update_user_statistics()
        
        logger.info("User deleted event processed successfully")
    
    @subscriber.handler("test.event")
    async def handle_test_event(event):
        """테스트 이벤트 처리"""
        event_data = event["data"]
        add_context(event_type="test.event")
        
        logger.info(
            "Processing test event",
            message=event_data.get("message"),
            user_id=event_data.get("user_id")
        )
        
        # 테스트 로직
        await process_test_message(event_data)
        
        logger.info("Test event processed successfully")


# 비즈니스 로직 함수들
async def send_welcome_email(user_data: dict):
    """환영 이메일 발송"""
    logger.info("Sending welcome email", user_id=user_data["user_id"])
    
    # 실제 구현에서는 이메일 서비스 호출
    # await email_service.send_welcome_email(
    #     to=user_data["email"],
    #     name=user_data["name"]
    # )
    
    logger.info("Welcome email sent successfully")


async def create_user_profile(user_data: dict):
    """사용자 프로필 생성"""
    logger.info("Creating user profile", user_id=user_data["user_id"])
    
    # 실제 구현에서는 프로필 서비스 호출
    # await profile_service.create_profile(
    #     user_id=user_data["user_id"],
    #     name=user_data["name"],
    #     email=user_data["email"]
    # )
    
    logger.info("User profile created successfully")


async def update_user_statistics():
    """사용자 통계 업데이트"""
    logger.info("Updating user statistics")
    
    # 실제 구현에서는 통계 서비스 호출
    # await statistics_service.update_user_count()
    
    logger.info("User statistics updated successfully")


async def update_email_subscriptions(user_id: str, new_email: str):
    """이메일 구독 정보 업데이트"""
    logger.info("Updating email subscriptions", user_id=user_id, new_email=new_email)
    
    # 실제 구현에서는 구독 서비스 호출
    # await subscription_service.update_email(user_id, new_email)
    
    logger.info("Email subscriptions updated successfully")


async def update_user_profile_name(user_id: str, new_name: str):
    """사용자 프로필 이름 업데이트"""
    logger.info("Updating user profile name", user_id=user_id, new_name=new_name)
    
    # 실제 구현에서는 프로필 서비스 호출
    # await profile_service.update_name(user_id, new_name)
    
    logger.info("User profile name updated successfully")


async def invalidate_user_cache(user_id: str):
    """사용자 캐시 무효화"""
    logger.info("Invalidating user cache", user_id=user_id)
    
    # 실제 구현에서는 캐시 서비스 호출
    # await cache_service.delete_pattern(f"user:{user_id}:*")
    
    logger.info("User cache invalidated successfully")


async def cleanup_user_data(user_id: str):
    """사용자 관련 데이터 정리"""
    logger.info("Cleaning up user data", user_id=user_id)
    
    # 실제 구현에서는 각 서비스별 정리 작업
    # await profile_service.delete_profile(user_id)
    # await subscription_service.cancel_all_subscriptions(user_id)
    # await analytics_service.anonymize_user_data(user_id)
    
    logger.info("User data cleanup completed successfully")


async def send_account_deletion_notification(user_id: str):
    """계정 삭제 알림 발송"""
    logger.info("Sending account deletion notification", user_id=user_id)
    
    # 실제 구현에서는 알림 서비스 호출
    # await notification_service.send_account_deletion_notification(user_id)
    
    logger.info("Account deletion notification sent successfully")


async def process_test_message(event_data: dict):
    """테스트 메시지 처리"""
    message = event_data.get("message", "")
    user_id = event_data.get("user_id")
    
    logger.info("Processing test message", message=message, user_id=user_id)
    
    # 테스트 로직
    if "error" in message.lower():
        logger.warning("Test message contains error keyword", message=message)
    elif "success" in message.lower():
        logger.info("Test message indicates success", message=message)
    
    logger.info("Test message processed successfully")