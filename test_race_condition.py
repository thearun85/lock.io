import threading
from src.core import DistributedLockService
import json

def race_condition(service: DistributedLockService, worker_id: int):
    result = service.create_session(f"client-{worker_id}")
    session_id = result['data']
    result = service.acquire_lock(session_id, f"resource-{worker_id}")

if __name__ == '__main__':
    print("Testing race condition")
    lock_service = DistributedLockService()
    threads = []
    for i in range(10):
        t = threading.Thread(target=race_condition, args=(lock_service, i))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print(f"{json.dumps(lock_service.get_service_stats(), indent=2)}")
    
