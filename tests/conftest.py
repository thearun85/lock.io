import pytest
from typing import Generator
import time
from src.core.lock_service import DistributedLockService

@pytest.fixture
def lock_service()-> Generator[DistributedLockService, None, None]:
    """
    Yield a fresh DistributedLockService for each test.

    Provides automatic cleanup of service state.
    """
    svc = DistributedLockService()
    yield svc

@pytest.fixture
def lock_service_with_session(lock_service) -> Generator[tuple[DistributedLockService, str], None, None]:
    """
    Yields a lock service with a pre-created session.

    Returns:
        tuple(DistributedLockService, session_id)
    """
    result = lock_service.create_session("client-1")
    session_id = result['data']

    yield lock_service, session_id

    # Cleanup
    result = lock_service.get_session_info(session_id)
    if result['success']:
        lock_service.delete_session(session_id)
        
@pytest.fixture
def lock_service_with_expired_session(lock_service) -> Generator[tuple[DistributedLockService, str], None, None]:
    """
    Yields a lock service with a pre-created session.

    Returns:
        tuple(DistributedLockService, session_id)
    """
    result = lock_service.create_session("client-1", timeout=5)
    session_id = result['data']
    time.sleep(6)
    
    yield lock_service, session_id

    # Cleanup
    result = lock_service.get_session_info(session_id)
    if result['success']:
        lock_service.delete_session(session_id)

@pytest.fixture
def lock_service_with_same_session_lock(lock_service) -> Generator[tuple[DistributedLockService, str, str, int], None, None]:
    """
    Yields a lock service with a pre-created session.

    Returns:
        tuple(DistributedLockService, session_id)
    """
    result = lock_service.create_session("client-1")
    session_id = result['data']

    result = lock_service.acquire_lock(session_id, "resource-1")

    yield lock_service, session_id, "resource-1", result['data']

    # Cleanup
    result = lock_service.get_session_info(session_id)
    if result['success']:
        lock_service.delete_session(session_id)

@pytest.fixture
def lock_service_with_another_session_lock(lock_service) -> Generator[tuple[DistributedLockService, str, str, int], None, None]:
    """
    Yields a lock service with a pre-created session.

    Returns:
        tuple(DistributedLockService, session_id)
    """
    result = lock_service.create_session("client-1")
    session_id_1 = result['data']

    result_1 = lock_service.acquire_lock(session_id_1, "resource-1")

    result_2 = lock_service.create_session("client-1")
    session_id_2 = result_2['data']
    yield lock_service, session_id_2, "resource-1", result_1['data']

    # Cleanup
    result = lock_service.get_session_info(session_id_1)
    if result['success']:
        lock_service.delete_session(session_id_1)
    result = lock_service.get_session_info(session_id_2)
    if result['success']:
        lock_service.delete_session(session_id_2)
