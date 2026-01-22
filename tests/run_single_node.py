import pytest
import time
from src.config import get_node_config
from src.lock_service import LockService


def main():
    self_address, partners = get_node_config()
    node = LockService(self_address, partners)

    time.sleep(5)

    assert node.is_leader() == True
    assert node.get_leader() == self_address

    session_id_1 = node.create_session("test-client-1", 10)
    assert session_id_1 is not None

    session_info = node.get_session_info(session_id_1)
    assert session_info is not None
    assert session_info['client_id'] == "test-client-1"
    assert session_info['session_id'] == session_id_1
    assert session_info['timeout'] == 10
    assert node._is_expired(session_info) == False

    stats = node.get_stats()
    print(f"stats is {stats}")
    success = node.delete_session(session_id_1)
    assert success == True
    session_info = node.get_session_info(session_id_1)
    assert session_info is None

    session_id_2 = node.create_session("test-client-2")
    assert session_id_2 is not None
    session_id_3 = node.create_session("test-client-3")
    assert session_id_3 is not None
    
    fence_1 = node.acquire_lock(session_id_2, "resource-2")
    assert fence_1 is not None
    fence_2 = node.acquire_lock(session_id_3, "resource-2")
    assert fence_2 is None
    
if __name__ == '__main__':
    main()
