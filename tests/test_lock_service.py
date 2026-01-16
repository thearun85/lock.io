import pytest
from src.lock_service import LockService
import time

@pytest.fixture
def lock_service():
    """Create a fresh lock service for each test"""
    return LockService()

def test_session_creation(lock_service):
    """Test that sessions can be created"""
    session_id = lock_service.create_session("test-client", timeout=60)
    assert session_id is not None
    session = lock_service.get_session(session_id)
    print(f"{session}")
    assert session is not None
    assert session.client_id == "test-client"
    assert session.timeout == 60

def test_lock_mutual_exclusion(lock_service):
    """Test that only one session cn hold a lock"""
    session1 = lock_service.create_session("test-client1", timeout=60)
    session2 = lock_service.create_session("test-client2", timeout=60)

    fence_1 = lock_service.acquire_lock(session1, "resource1")
    assert fence_1 is not None
    
    fence_2 = lock_service.acquire_lock(session2, "resource1")
    assert fence_2 is None

    release_fence_1 = lock_service.release_lock(session1, "resource1", fence_1)
    assert release_fence_1 == True

    fence_2 = lock_service.acquire_lock(session2, "resource1")
    assert fence_2 is not None

    release_fence_2 = lock_service.release_lock(session1, "resource_1", fence_1)
    assert release_fence_2 == False

def test_session_expiry_and_cleanup(lock_service):
    """Test cleanup removes expired sessions and releases locks"""
    session1 = lock_service.create_session("test-client1", timeout=1)
    assert session1 is not None
    fence_1 = lock_service.acquire_lock(session1, "resource-1")
    assert fence_1 is not None
    time.sleep(2)
    cleaned = lock_service.cleanup_expired_sessions()
    assert cleaned == 1

    session2 = lock_service.create_session("test-client2", timeout=60)
    fence_2 = lock_service.acquire_lock(session2, "resource-1")
    assert fence_2 is not None
