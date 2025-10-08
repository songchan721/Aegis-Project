import pytest
from aegis_shared.errors.exceptions import AegisBaseException, ServiceException
# from aegis_shared.errors.handlers import aegis_exception_handler

def test_aegis_base_exception():
    with pytest.raises(AegisBaseException):
        raise AegisBaseException("TEST_001", "Test error")

def test_service_exception():
    with pytest.raises(ServiceException):
        raise ServiceException("TEST_002", "Test service error")

@pytest.mark.asyncio
async def test_aegis_exception_handler():
    # This would be tested in integration tests with a mock request.
    # aegis_exception_handler is not implemented yet
    pass
