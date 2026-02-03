import pytest
from typing import Generator
import time
from src.core.lock_service import DistributedLockService
import requests

API_BASE_URL = "http://localhost:5000/sessions"


@pytest.fixture
def lock_service()-> Generator[DistributedLockService, None, None]:
    """
    Yield a fresh DistributedLockService for each test.

    Provides automatic cleanup of service state.
    """
    svc = DistributedLockService("localhost:4321", [])
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


@pytest.fixture
def valid_session() -> Generator[dict, None, None]:
    """Yield a new session for each test"""
    response = requests.post(
            url = f"{API_BASE_URL}",
            json={"client_id": "client-1", "timeout": 100}
        )
    assert response.status_code == 201
    result = response.json()
    session_id = result['session_id']
    yield result

    response =  requests.get(
                url = f"{API_BASE_URL}/{session_id}",
                json={}
            )

    if response.status_code == 200:
        response =  requests.delete(
                        url = f"{API_BASE_URL}/{session_id}",
                        json={}
                    )

@pytest.fixture
def valid_session_with_lock() -> Generator[tuple[str, str, int], None, None]:
    """Yield a new session for each test"""
    response = requests.post(
            url = f"{API_BASE_URL}",
            json={"client_id": "client-2", "timeout": 100}
        )
    assert response.status_code == 201
    result = response.json()
    session_id_1 = result['session_id']

    resource_1 = "resource-1"
    response = requests.post(
        url = f"{API_BASE_URL}/{session_id_1}/locks/{resource_1}",
        json={}
    )
    assert response.status_code == 201
    result = response.json()
    fence_token = result['fence_token']
    yield session_id_1, resource_1, fence_token

    response =  requests.get(
                url = f"{API_BASE_URL}/{session_id_1}",
                json={}
            )
    if response.status_code == 200:
        response =  requests.delete(
                        url = f"{API_BASE_URL}/{session_id_1}",
                        json={}
                    )

@pytest.fixture
def expired_session() -> Generator[dict, None, None]:
    """Yield a new session for each test"""
    response = requests.post(
            url = f"{API_BASE_URL}",
            json={"client_id": "client-1", "timeout": 5}
        )
    assert response.status_code == 201
    result = response.json()
    time.sleep(6)
    yield result

