import pytest
from src.lock_service import LockService
import time

@pytest.fixture
def lock_service():
    """Create a new lock service for each test"""
    return LockService()

def test_session(lock_service):
    """Test sessions"""
    session_id_1 = lock_service.create_session("test-client-1", timeout=60)
    assert session_id_1 is not None

    session_1_info = lock_service.get_session_info(session_id_1)
    assert session_1_info is not None
    assert session_1_info['session_id'] == session_id_1
    assert session_1_info['client_id'] == "test-client-1"
    assert session_1_info['timeout'] == 60
    assert session_1_info['expired'] == False

    deleted_1 = lock_service.delete_session(session_id_1)

    assert deleted_1 == True
    session_1_info = lock_service.get_session_info(session_id_1)
    assert session_1_info is None

    session_id_2 = lock_service.create_session("test-client-2", timeout=5)
    assert session_id_2 is not None
    time.sleep(4)
    lock_service.keepalive(session_id_2)
    time.sleep(2)
    session_2_info = lock_service.get_session_info(session_id_2)
    assert session_2_info is not None

def test_locks(lock_service):
    """Test lock functionality"""
    
    session_id_1 = lock_service.create_session("test-client-1", timeout=60)
    assert session_id_1 is not None 

    fence_1 = lock_service.acquire_lock(session_id_1, "resource-1")
    assert fence_1 is not None

    lock_1_info = lock_service.get_lock_info("resource-1")
    assert lock_1_info is not None
    assert lock_1_info['session_id'] == session_id_1
    assert lock_1_info['resource'] == "resource-1"
    assert lock_1_info['fence_token'] == fence_1

    released = lock_service.release_lock(session_id_1, "resource-1", fence_1)
    assert released == True

    session_id_2 = lock_service.create_session("test-client-2", timeout=5)
    assert session_id_2 is not None 

    fence_2 = lock_service.acquire_lock(session_id_2, "resource-2")
    assert fence_2 is not None

    session_id_3 = lock_service.create_session("test-client-3", timeout=5)
    assert session_id_3 is not None
     
    fence_3 = lock_service.acquire_lock(session_id_3, "resource-2")
    assert fence_3 is None

    time.sleep(6)
    cleaned = lock_service.cleanup_expired_sessions()
    assert cleaned == True
