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

@pytest.mark.unit
def test_create_valid_session(lock_service):
    """Test creating a session with client id and timeout"""
    print("Test valid session creation")
    result = lock_service.create_session(client_id="client-1", timeout=90)
    assert result['success'] is True
    session_id = result['data']
    assert session_id is not None
    assert len(session_id) == 36

    result = lock_service.get_session_info(session_id)
    assert result['success'] == True
    session = result['data']
    assert session['client_id'] == "client-1"
    assert session['timeout'] == 90

@pytest.mark.unit
def test_create_session_with_default_timeout(lock_service):
    """Test create session with default timeout"""
    result = lock_service.create_session("client-1")
    session_id = result['data']
    result = lock_service.get_session_info(session_id)
    session = result['data']
    assert session['timeout'] == 60

@pytest.mark.unit
def test_get_session_info(lock_service_with_session):
    """Test query session details"""
    service, session_id = lock_service_with_session
    result = service.get_session_info(session_id)
    session = result['data']
    assert session['session_id'] == session_id
    assert session['client_id'] == "client-1"
    assert session['timeout'] == 60
    assert session.get('created_at') is not None
    assert session.get('last_keepalive') is not None
    assert session['locks_held'] == []

@pytest.mark.unit
def test_is_expired(lock_service):
    result = lock_service.create_session("client-1", 5)
    session_id = result['data']
    
    result = lock_service.get_session_info(session_id)
    session = result['data']
    assert session['is_expired'] == False
    
    time.sleep(6)
    result = lock_service.get_session_info(session_id)
    session = result['data']
    assert session['is_expired'] == True
    
@pytest.mark.unit
def test_keepalive(lock_service_with_session):
    """Test update keepalive for a session"""
    service, session_id = lock_service_with_session
    result = service.update_keepalive(session_id)
    assert result['success'] == True

@pytest.mark.unit
def test_delete_session(lock_service_with_session):
    """Test delete session with valid and invalid session id's"""
    service, session_id = lock_service_with_session

    # Test deletion of valid session id
    result = service.get_session_info(session_id)
    session = result['data']
    assert session['is_expired'] == False
    
    result = service.delete_session(session_id)
    assert result['success'] == True

    
    result = service.get_session_info(session_id)
    assert result['success'] == False
    
    result = service.delete_session(session_id)
    assert result['success'] == False

