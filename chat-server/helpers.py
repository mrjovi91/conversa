import uuid, M2Crypto

def generate_session_id(num_bytes = 16):
    return uuid.UUID(bytes = M2Crypto.m2.rand_bytes(num_bytes))
