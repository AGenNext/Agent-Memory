#!/usr/bin/env python3
"""
Capability: SurrealQL Functions

SurrealQL built-in functions as Python tools.
Reference: https://surrealdb.com/docs/surrealql/functions
"""

import asyncio
from surrealdb import Surreal
from typing import Any


class SurrealQLFunctions:
    """SurrealQL function tools."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "functions", "database": "tools"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- String Functions -----
    
    async def string_split(self, text: str, delimiter: str) -> list:
        """Split string."""
        return await self.db.query(
            "RETURN string::split($text, $delim)",
            {"text": text, "delim": delimiter}
        )
    
    async def string_upper(self, text: str) -> str:
        """Uppercase."""
        return await self.db.query(
            "RETURN string::upper($text)",
            {"text": text}
        )
    
    async def string_lower(self, text: str) -> str:
        """Lowercase."""
        return await self.db.query(
            "RETURN string::lower($text)",
            {"text": text}
        )
    
    async def string_trim(self, text: str) -> str:
        """Trim whitespace."""
        return await self.db.query(
            "RETURN string::trim($text)",
            {"text": text}
        )
    
    async def string_replace(self, text: str, old: str, new: str) -> str:
        """Replace text."""
        return await self.db.query(
            "RETURN string::replace($text, $old, $new)",
            {"text": text, "old": old, "new": new}
        )
    
    async def string_join(self, delimiter: str, texts: list) -> str:
        """Join strings."""
        return await self.db.query(
            "RETURN string::join($delim, $texts)",
            {"delim": delimiter, "texts": texts}
        )
    
    # ----- Math Functions -----
    
    async def math_sum(self, numbers: list) -> float:
        """Sum numbers."""
        return await self.db.query(
            "RETURN math::sum($nums)",
            {"nums": numbers}
        )
    
    async def math_mean(self, numbers: list) -> float:
        """Average."""
        return await self.db.query(
            "RETURN math::mean($nums)",
            {"nums": numbers}
        )
    
    async def math_min(self, numbers: list) -> float:
        """Minimum."""
        return await self.db.query(
            "RETURN math::min($nums)",
            {"nums": numbers}
        )
    
    async def math_max(self, numbers: list) -> float:
        """Maximum."""
        return await self.db.query(
            "RETURN math::max($nums)",
            {"nums": numbers}
        )
    
    async def math_random(self, min_val: int = 0, max_val: int = 100) -> int:
        """Random number."""
        return await self.db.query(
            "RETURN math::rand($min, $max)",
            {"min": min_val, "max": max_val}
        )
    
    async def math_round(self, number: float) -> int:
        """Round number."""
        return await self.db.query(
            "RETURN math::round($num)",
            {"num": number}
        )
    
    # ----- Time Functions -----
    
    async def time_now(self) -> str:
        """Current time."""
        return await self.db.query("RETURN time::now()")
    
    async def time_epoch(self) -> int:
        """Unix epoch."""
        return await self.db.query("RETURN time::epoch()")
    
    async def time_format(self, timestamp: str, format: str = "%Y-%m-%d") -> str:
        """Format time."""
        return await self.db.query(
            "RETURN time::format($ts, $fmt)",
            {"ts": timestamp, "fmt": format}
        )
    
    async def time_add(self, timestamp: str, duration: str) -> str:
        """Add duration."""
        return await self.db.query(
            "RETURN time::now() + $duration",
            {"duration": duration}
        )
    
    # ----- Array Functions -----
    
    async def array_combine(self, arr1: list, arr2: list) -> list:
        """Combine arrays."""
        return await self.db.query(
            "RETURN array::combine($a1, $a2)",
            {"a1": arr1, "a2": arr2}
        )
    
    async def array_find(self, arr: list, value: Any) -> int:
        """Find index."""
        return await self.db.query(
            "RETURN array::find($arr, $val)",
            {"arr": arr, "val": value}
        )
    
    async def array_slice(self, arr: list, start: int, end: int) -> list:
        """Slice array."""
        return await self.db.query(
            "RETURN array::slice($arr, $start, $end)",
            {"arr": arr, "start": start, "end": end}
        )
    
    # ----- Object Functions -----
    
    async def object_keys(self, obj: dict) -> list:
        """Object keys."""
        return await self.db.query(
            "RETURN object::keys($obj)",
            {"obj": obj}
        )
    
    async def object_values(self, obj: dict) -> list:
        """Object values."""
        return await self.db.query(
            "RETURN object::values($obj)",
            {"obj": obj}
        )
    
    async def object_merge(self, obj1: dict, obj2: dict) -> dict:
        """Merge objects."""
        return await self.db.query(
            "RETURN object::merge($o1, $o2)",
            {"o1": obj1, "o2": obj2}
        )
    
    # ----- Crypto Functions -----
    
    async def crypto_md5(self, text: str) -> str:
        """MD5 hash."""
        return await self.db.query(
            "RETURN crypto::md5($text)",
            {"text": text}
        )
    
    async def crypto_sha256(self, text: str) -> str:
        """SHA256 hash."""
        return await self.db.query(
            "RETURN crypto::sha256($text)",
            {"text": text}
        )
    
    # ----- Vector Functions -----
    
    async def vector_distance(self, v1: list, v2: list, method: str = "cosine") -> float:
        """Vector distance."""
        return await self.db.query(
            f"RETURN vector::distance::{method}($v1, $v2)",
            {"v1": v1, "v2": v2}
        )
    
    async def vector_similar(self, v1: list, v2: list) -> float:
        """Cosine similarity."""
        return await self.db.query(
            "RETURN vector::similarity::cosine($v1, $v2)",
            {"v1": v1, "v2": v2}
        )


async def demo():
    """Demo functions."""
    fns = SurrealQLFunctions()
    await fns.connect()
    
    print("String:", await fns.string_upper("hello"))
    print("Math:", await fns.math_mean([1, 2, 3, 4, 5]))
    print("Time:", await fns.time_now())


if __name__ == "__main__":
    asyncio.run(demo())