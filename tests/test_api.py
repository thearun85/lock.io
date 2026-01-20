"""Test script for the Flask API"""
import requests
import json
import time
BASE_URL = "http://localhost:5000"

def test_full_workflow():
    print("Testing Lock Service API...")

    # Session Creation
    print("Test session creation\n")
    response = requests.post(f"{BASE_URL}/sessions", json={"client_id": "test-client-1", "timeout": 5})
    assert response.status_code == 201
    session_data = response.json()
    print(f"Session data is {json.dumps(session_data, indent=2)}")
    print("Test session creation successful")

    # Session information
    print("\nTest get session info")
    response = requests.get(f"{BASE_URL}/sessions/{session_data['session_id']}" )
    assert response.status_code == 200
    print(f"Session information is {json.dumps(response.json(), indent=2)}")

    print("\n Get session information successful\n")
    time.sleep(6)

    # Session Timeout
    response = requests.get(f"{BASE_URL}/sessions/{session_data['session_id']}" )
    assert response.status_code == 200
    session_data = response.json()
    assert session_data['expired'] == True
    print("session timedout")


    # Lock Creation
    response = requests.post(f"{BASE_URL}/sessions", json={"client_id": "test-client-1", "timeout": 5})
    assert response.status_code == 201
    session_data1 = response.json()
    session_id_1 = session_data1['session_id']
    resource_1 = "resource-1"
    response = requests.post(f"{BASE_URL}/sessions/{session_id_1}/locks/{resource_1}")
    assert response.status_code == 201
    lock_data1 = response.json()
    assert lock_data1['acquired'] == True
    print("\n Lock creation tested")

    # Mutual exclusion - Session 2 creation
    print("\n testing mutual exclusion")
    response = requests.post(f"{BASE_URL}/sessions", json={"client_id": "test-client-2", "timeout": 5})
    assert response.status_code == 201
    session_data2 = response.json()
    session_id_2 = session_data2['session_id']
    
    response = requests.post(f"{BASE_URL}/sessions/{session_id_2}/locks/{resource_1}")
    assert response.status_code == 409
    lock_data1 = response.json()
    assert lock_data1['acquired'] == False
    print("\n Mutual exclusion working")

    response = requests.delete(f"{BASE_URL}/sessions/{session_id_1}")
    assert response.status_code == 200
    response = requests.delete(f"{BASE_URL}/sessions/{session_id_2}")
    assert response.status_code == 200
    print("\n Session deletion working")

    # Service stats
    response = requests.get(f"{BASE_URL}/stats")
    assert response.status_code == 200
    print(f"Service stat is {json.dumps(response.json(), indent=2)}")
    response = requests.post(f"{BASE_URL}/admin/cleanup")
    response = requests.get(f"{BASE_URL}/stats")
    assert response.status_code == 200
    print(f"Service stat after cleanup is {json.dumps(response.json(), indent=2)}")

    
if __name__ == '__main__':
    test_full_workflow()
