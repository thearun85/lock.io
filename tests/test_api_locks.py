"""
Distributed Lock Service - Test for Public API's for locks
"""
import pytest
import requests

API_BASE_LOCK_URL = "http://localhost:5000/sessions"

@pytest.mark.unit
def test_acquire_lock_with_session(valid_session):

    result = valid_session
    session_id = result['session_id']
    resource = "resource-1"
    result = requests.post(
        url=f"{API_BASE_LOCK_URL}/{session_id}/locks/{resource}",
        json={}
    )
    assert result.status_code == 201
    response = result.json()
    assert response['acquired'] == True
    assert response['session_id'] == session_id
    assert response['resource'] == resource
    assert response['fence_token'] > 0

@pytest.mark.unit
def test_acquire_lock_with_invalid_session():

    session_id = " "
    resource = "resource-1"
    result = requests.post(
        url=f"{API_BASE_LOCK_URL}/{session_id}/locks/{resource}",
        json={}
    )
    assert result.status_code == 400
    response = result.json()
    assert response['acquired'] == False
    assert response['error'] == "Session ID must be a non-empty string"

@pytest.mark.unit
def test_acquire_lock_with_invalid_resource(valid_session):

    result = valid_session
    session_id = result['session_id']
    resource = " "
    result = requests.post(
        url=f"{API_BASE_LOCK_URL}/{session_id}/locks/{resource}",
        json={}
    )
    assert result.status_code == 400
    response = result.json()
    assert response['acquired'] == False
    assert response['error'] == "Resource must be a non-empty string"

@pytest.mark.unit
def test_acquire_lock_with_resource_exceeds_255(valid_session):

    result = valid_session
    session_id = result['session_id']
    resource = "asdfghjklasdfghjklasdfghjklasdfghjjklasdfghhjjkkllasdfghjklqwertyuioqwertyuiioqwertyuiooqwertyuioqwertyuiopqasdfghjklasdfghjklasdfghjklasdfghjjklasdfghhjjkkllasdfghjklqwertyuioqwertyuiioqwertyuiooqwertyuioqwertyuiopqasdfghjklasdfghjklasdfghjklasdfghjjklasdfghhjjkkllasdfghjklqwertyuioqwertyuiioqwertyuiooqwertyuioqwertyuiopq"
    result = requests.post(
        url=f"{API_BASE_LOCK_URL}/{session_id}/locks/{resource}",
        json={}
    )
    assert result.status_code == 400
    response = result.json()
    assert response['acquired'] == False
    assert response['error'] == "Resource cannot exceed 255 characters"

@pytest.mark.unit
def test_acquire_lock_mutual_exclusion(valid_session_with_lock, valid_session):

    session_id_1, resource_1, fence_token_1 = valid_session_with_lock
    result = valid_session
    session_id_2 = result['session_id']
    
    result = requests.post(
        url=f"{API_BASE_LOCK_URL}/{session_id_2}/locks/{resource_1}",
        json={}
    )
    assert result.status_code == 400
    response = result.json()
    assert response['acquired'] == False
    assert response['error'] == f"Resource {resource_1} already locked by another session"
