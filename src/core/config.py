"""
Distributed Lock Service - Configuration management
"""
import os

def validate_address(address: str, name: str) -> bool:
    if ":" not in address:
        raise ValueError(f"{name} must be in 'host:port' format, got :{address}")

    host, port = address.split(":")
    if not host:
        raise ValueError(f"{name} must be in 'host:port' format, got {address}")

    try:
        port_num = int(port)
        if port_num < 0 or port_num > 65535:    
            raise ValueError(f"{name} port must be between 1 and 65535, got :{port}")
    except ValueError:
        raise ValueError(f"{name} has invalid port: {address}")

def get_node_config() ->tuple[str, list[str]]:
    """
    Validate and return the self_address and partner_addresses.
    These are used to run the Raft cluster. Obtain them from the environment variables.
    """
    self_address = os.getenv("SELF_ADDRESS")
    if not self_address:
        raise ValueError("SELF_ADDRESS environment variable must be set")

    validate_address(self_address, "SELF_ADDRESS")

    partner_addresses = []
    partner_addresses_str = os.getenv("PARTNER_ADDRESSES")
    if partner_addresses_str:
        
        for addr in partner_addresses_str.split(","):
            addr = addr.strip()
            if addr:
                validate_address(addr, f"PARTNER_ADDRES-{addr}")
                partner_addresses.append(addr)

    return self_address, partner_addresses

def get_api_port() -> int:
    api_port = int(os.getenv("API_PORT", "5000"))
    return api_port
