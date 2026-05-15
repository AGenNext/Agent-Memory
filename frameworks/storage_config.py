"""
Storage Configuration - Switch between SurrealDB backends

Usage:
    from frameworks.storage_config import get_storage, StorageBackend
    
    # RocksDB (default)
    db = get_storage(StorageBackend.ROCKSDB, path="/data/db")
    
    # SurrealKV (modern)
    db = get_storage(StorageBackend.SURREALKV, path="/data/db")
    
    # In-memory (fast)
    db = get_storage(StorageBackend.MEMORY)
    
    # Distributed (TiKV)
    db = get_storage(StorageBackend.TIKV, address="127.0.0.1:2379")
"""

import os
from enum import Enum
from typing import Optional


class StorageBackend(Enum):
    """Storage backends"""
    MEMORY = "memory"
    ROCKSDB = "rocksdb"
    SURREALKV = "surrealkv"
    TIKV = "tikv"
    FILE = "file"


class StorageConfig:
    """Storage configuration"""
    
    def __init__(
        self,
        backend: StorageBackend = StorageBackend.ROCKSDB,
        path: Optional[str] = None,
        address: Optional[str] = None,
        user: str = "root",
        password: str = "root",
    ):
        self.backend = backend
        self.path = path or "/data/memory.db"
        self.address = address or "127.0.0.1:2379"
        self.user = user
        self.password = password
    
    def get_url(self) -> str:
        """Get SurrealDB connection URL"""
        if self.backend == StorageBackend.MEMORY:
            return f"mem://{self.user}:{self.password}@memory"
        
        elif self.backend == StorageBackend.ROCKSDB:
            return f"rocksdb://{self.user}:{self.password}@{self.path}"
        
        elif self.backend == StorageBackend.SURREALKV:
            return f"surrealkv://{self.user}:{self.password}@{self.path}"
        
        elif self.backend == StorageBackend.TIKV:
            return f"tikv://{self.user}:{self.password}@{self.address}"
        
        else:
            return f"file://{self.user}:{self.password}@{self.path}"
    
    def get_docker_command(self) -> str:
        """Get docker run command"""
        if self.backend == StorageBackend.MEMORY:
            return 'surreal start --user root --pass root memory'
        
        elif self.backend == StorageBackend.ROCKSDB:
            return f'surreal start --user root --pass root rocksdb:///{self.path}'
        
        elif self.backend == StorageBackend.SURREALKV:
            return f'surreal start --user root --pass root surrealkv:///{self.path}'
        
        return 'surreal start --user root --pass root memory'
    
    def to_dict(self) -> dict:
        return {
            "backend": self.backend.value,
            "path": self.path,
            "address": self.address,
            "user": self.user,
        }


def get_storage(
    backend: StorageBackend = StorageBackend.ROCKSDB,
    **kwargs
) -> StorageConfig:
    """Get storage config"""
    return StorageConfig(backend=backend, **kwargs)


# Presets
STORAGE_PRESETS = {
    "dev": StorageConfig(backend=StorageBackend.MEMORY),
    "prod": StorageConfig(backend=StorageBackend.ROCKSDB, path="/data/surrealdb"),
    "kv": StorageConfig(backend=StorageBackend.SURREALKV, path="/data/surrealdb"),
    "distributed": StorageConfig(backend=StorageBackend.TIKV, address="127.0.0.1:2379"),
}


# Example
if __name__ == "__main__":
    # Default (RocksDB)
    storage = get_storage(StorageBackend.ROCKSDB)
    print(f"URL: {storage.get_url()}")
    print(f"Docker: {storage.get_docker_command()}")
    
    # Memory
    memory = get_storage(StorageBackend.MEMORY)
    print(f"\nMemory: {memory.get_url()}")
    
    # SurrealKV
    kv = get_storage(StorageBackend.SURREALKV, path="/data/myapp.db")
    print(f"\nSurrealKV: {kv.get_url()}")