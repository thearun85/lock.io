import pytest
import time

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
def test_is_expired(lock_service_with_expired_session):
    service, session_id = lock_service_with_expired_session
    
    result = service.get_session_info(session_id)
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

@pytest.mark.unit
def test_create_session_with_lock(lock_service_with_same_session_lock):

    svc, session_id, resource, fence_token = lock_service_with_same_session_lock

    assert fence_token > 0
    result = svc.get_session_info(session_id)
    assert result['success'] == True
    session = result['data']
    assert len(session['locks_held']) == 1
    lock = svc.lock_status(resource)
    assert lock['data'] == session_id

@pytest.mark.unit
def test_delete_session_with_lock(lock_service_with_same_session_lock):

    svc, session_id, resource, fence_token = lock_service_with_same_session_lock

    assert fence_token > 0
    result = svc.get_session_info(session_id)
    assert result['success'] == True
    session = result['data']
    assert len(session['locks_held']) == 1
    
    lock = svc.lock_status(resource)
    assert lock['data'] == session_id

    result = svc.delete_session(session_id)
    assert result['success'] == True

    lock = svc.lock_status(resource)
    assert lock['data'] is None
    
    
@pytest.mark.unit
def test_expired_session_cleanup(lock_service_with_expired_session):
    service, session_id = lock_service_with_expired_session
        
    result = service.get_session_info(session_id)
    session = result['data']
    assert session['is_expired'] == True

    result = service.get_service_stats()
    assert result['success'] == True
    data = result['data']
    assert data['total_sessions'] > 0
    count = service.cleanup_expired_sessions()
    assert count > 0

@pytest.mark.unit
def test_service_stats(lock_service_with_session, lock_service_with_expired_session, lock_service_with_same_session_lock):
    service1, session_id1 = lock_service_with_session
    service2, session_id2 = lock_service_with_expired_session
    service3, session_i3, resourc3, fence_toke3 = lock_service_with_same_session_lock
    
    result = service1.get_service_stats()
    assert result['success'] == True
    data = result['data']
    assert data['total_sessions'] > 0
    assert data['expired_sessions'] > 0
    assert data['fence_counter'] > 0
    assert data['total_locks'] > 0
