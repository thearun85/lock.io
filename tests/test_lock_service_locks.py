"""Distributed Lock Service - Test lock management"""
import pytest

@pytest.mark.unit
def test_acquire_lock_with_valid_session(lock_service_with_session):
    """Test lock acquisition on a resource with a valid session"""
    service, session_id = lock_service_with_session

    result = service.acquire_lock(session_id, "resource-1")
    assert result['success'] == True
    assert result['data'] > 0

@pytest.mark.unit
def test_valid_acquire_lock_invalid_session(lock_service):
    """Test lock acquisition on a resource with a valid session"""
    service = lock_service

    result = service.acquire_lock(1, "resource-1")
    assert result['success'] == False
    assert result['err_msg'] in "Session 1 does not exist"

@pytest.mark.unit
def test_valid_acquire_lock_expired_session(lock_service_with_expired_session):
    """Test lock acquisition on a resource with a valid session"""
    service, session_id = lock_service_with_expired_session

    result = service.acquire_lock(session_id, "resource-1")
    assert result['success'] == False
    assert result['err_msg'] in f"Session {session_id} has expired"

@pytest.mark.unit
def test_acquire_lock_already_locked_by_this_session(lock_service_with_same_session_lock):
    """Test lock acquisition on a resource with a valid session"""
    service, session_id, resource, fence_token = lock_service_with_same_session_lock

    result = service.acquire_lock(session_id, resource)
    assert result['success'] == True
    assert result['data'] > 0

@pytest.mark.unit
def test_acquire_lock_already_locked_by_another_session(lock_service_with_another_session_lock):
    """Test lock acquisition on a resource with a valid session"""
    service, session_id, resource, _ = lock_service_with_another_session_lock

    result = service.acquire_lock(session_id, resource)
    assert result['success'] == False
    assert result['err_msg'] in f"Resource {resource} already locked by another session"

@pytest.mark.unit
def test_release_lock_with_valid_session(lock_service_with_same_session_lock):
    """Test lock acquisition on a resource with a valid session"""
    service, session_id, resource, fence_token = lock_service_with_same_session_lock

    result = service.release_lock(session_id, resource, fence_token)
    assert result['success'] == True

    result = service.lock_status(resource)
    assert result['success'] == True
    assert result['data'] == None

@pytest.mark.unit
def test_release_lock_on_non_existent_lock(lock_service_with_session):
    """Test lock acquisition on a resource with a valid session"""
    service, session_id = lock_service_with_session

    result = service.release_lock(session_id, "resource-1", 364856)
    assert result['success'] == False
    assert result['err_msg'] == "No lock exists on resource resource-1"

@pytest.mark.unit
def test_release_lock_with_invalid_fence_token(lock_service_with_same_session_lock):
    """Test lock acquisition on a resource with a valid session"""
    service, session_id, resource, fence_token = lock_service_with_same_session_lock

    result = service.release_lock(session_id, resource, 765462756)
    assert result['success'] == False
    assert result['err_msg'] == "Fence token 765462756 mismatch"

@pytest.mark.unit
def test_release_lock_with_invalid_fence_token(lock_service_with_another_session_lock):
    """Test lock acquisition on a resource with a valid session"""
    service, session_id, resource, fence_token = lock_service_with_another_session_lock

    result = service.release_lock(session_id, resource, fence_token)
    assert result['success'] == False
    assert result['err_msg'] == f"Session {session_id} does not own this resource {resource}"
