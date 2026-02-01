import pytest
import requests
from typing import Generator
import time

SESSIONS_BASE_URL = "http://localhost:5000/sessions"

@pytest.fixture
def valid_session() -> Generator[dict, None, None]:
    """Yield a new session for each test"""
    response = requests.post(
            url = f"{SESSIONS_BASE_URL}",
            json={"client_id": "client-1", "timeout": 100}
        )
    assert response.status_code == 201
    result = response.json()
    yield result

@pytest.fixture
def expired_session() -> Generator[dict, None, None]:
    """Yield a new session for each test"""
    response = requests.post(
            url = f"{SESSIONS_BASE_URL}",
            json={"client_id": "client-1", "timeout": 5}
        )
    assert response.status_code == 201
    result = response.json()
    time.sleep(6)
    yield result

@pytest.mark.unit
def test_create_session_with_valid_params():
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json={"client_id": "client-1", "timeout": 100}
    )
    assert response.status_code == 201
    session = response.json()
    assert len(session['session_id']) == 36
    assert session['client_id'] == "client-1"
    assert session['timeout'] == 100
    assert session['keepalive_interval'] == session['timeout']//3

@pytest.mark.unit
def test_create_session_with_missing_client_id():
    # Missing client_id in request json
    request = {}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "client_id is required"

@pytest.mark.unit
def test_create_session_with_non_string_client_id():
    # Non-string client_id
    request = {"client_id": 100}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "client_id must be a string"

@pytest.mark.unit
def test_create_session_with_empty_client_id():
    # Empty client_id
    request = {"client_id": ""}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "client_id is required"

@pytest.mark.unit
def test_create_session_with_whitespace_client_id():
    # client_id with whitespace
    request = {"client_id": "     "}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "client_id must be non-empty"

@pytest.mark.unit
def test_create_session_with_client_id_exceed_255():
    # client_id cannot exceed 255 characters
    request = {"client_id": "asdfghjklasdfghjklasdfghjklasdfghjjklasdfghhjjkkllasdfghjklqwertyuioqwertyuiioqwertyuiooqwertyuioqwertyuiopqasdfghjklasdfghjklasdfghjklasdfghjjklasdfghhjjkkllasdfghjklqwertyuioqwertyuiioqwertyuiooqwertyuioqwertyuiopqasdfghjklasdfghjklasdfghjklasdfghjjklasdfghhjjkkllasdfghjklqwertyuioqwertyuiioqwertyuiooqwertyuioqwertyuiopq"}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "client_id cannot exceed 255 characters"

@pytest.mark.unit
def test_create_session_with_default_timeout():
    # Missing client_id in request json
    request = {"client_id": "client-1"}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 201
    result = response.json()
    assert result['timeout'] == 60

@pytest.mark.unit
def test_create_session_with_timeout_bound_validations():
    # timeout less than 5 seconds
    request = {"client_id": "client-1", "timeout": 2}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "timeout must be between 5 and 3600 seconds"
     # timeout exceeds 3600 seconds
    request = {"client_id": "client-1", "timeout": 4000}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "timeout must be between 5 and 3600 seconds"
@pytest.mark.unit
def test_create_session_with_timeout_not_an_integer():
    # timeout is not an integer
    request = {"client_id": "client-1", "timeout": " "}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "timeout must be an integer"

@pytest.mark.unit
def test_create_session_with_empty_client_id():
    # Empty client_id
    request = {"client_id": ""}
    response = requests.post(
        url = f"{SESSIONS_BASE_URL}",
        json=request
    )

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"] == "client_id is required"

@pytest.mark.unit
def test_get_valid_session_info(valid_session):
    """Test get session info"""
    session_id = valid_session["session_id"]
    response = requests.get(
        f"{SESSIONS_BASE_URL}/{session_id}"
    )
    assert response.status_code == 200
    result = response.json()
    assert result['session_id'] == valid_session['session_id']
    assert result['client_id'] == "client-1"
    assert result['timeout'] == valid_session["timeout"]
    assert result['created_at'] > 0
    assert result['last_keepalive'] > 0
    assert result['is_expired'] == False

@pytest.mark.unit
def test_get_expired_session_info(expired_session):
    """Test get expired session info"""
    session_id = expired_session["session_id"]
    response = requests.get(
        f"{SESSIONS_BASE_URL}/{session_id}"
    )
    assert response.status_code == 200
    result = response.json()
    assert result['session_id'] == expired_session['session_id']
    assert result['client_id'] == "client-1"
    assert result['timeout'] == expired_session["timeout"]
    assert result['created_at'] > 0
    assert result['last_keepalive'] > 0
    assert result['is_expired'] == True

@pytest.mark.unit
def test_get_non_existent_session_info():
    """Test get non-existent session info"""
    response = requests.get(
        f"{SESSIONS_BASE_URL}/4976734697873496"
    )
    assert response.status_code == 404
    result = response.json()
    assert result['session_id'] == "4976734697873496"
    assert result['error'] == "Session 4976734697873496 does not exist"

@pytest.mark.unit
def test_keepalive_valid_session(valid_session):
    """Test keepalive valid session"""
    session_id = valid_session["session_id"]
    response = requests.post(
        f"{SESSIONS_BASE_URL}/{session_id}/keepalive"
    )
    assert response.status_code == 200
    result = response.json()
    assert result['session_id'] == valid_session['session_id']
    assert result['updated'] == True

@pytest.mark.unit
def test_keepalive_expired_session(expired_session):
    """Test keepalive expired session"""
    session_id = expired_session["session_id"]
    response = requests.post(
        f"{SESSIONS_BASE_URL}/{session_id}/keepalive"
    )
    assert response.status_code == 410
    result = response.json()
    assert result['session_id'] == expired_session['session_id']
    assert result['updated'] == False
    assert result['error'] == f"Session {session_id} has expired"
@pytest.mark.unit
def test_delete_valid_session(valid_session):
    """Test delete valid session"""
    session_id = valid_session["session_id"]
    response = requests.delete(
        f"{SESSIONS_BASE_URL}/{session_id}"
    )
    assert response.status_code == 200
    result = response.json()
    assert result['session_id'] == valid_session['session_id']
    assert result['deleted'] == True

    session_id = valid_session["session_id"]
    response = requests.get(
        f"{SESSIONS_BASE_URL}/{session_id}"
    )
    assert response.status_code == 404
    result = response.json()
    assert result["error"] == f"Session {session_id} does not exist"

@pytest.mark.unit
def test_delete_non_existent_session():
    """Test delete non-existent session"""
    session_id = "382658234648523"
    response = requests.delete(
        f"{SESSIONS_BASE_URL}/{session_id}"
    )
    assert response.status_code == 404
    result = response.json()
    assert result['session_id'] == session_id
    assert result['deleted'] == False
    assert result["error"] == "Session 382658234648523 does not exist"
        

