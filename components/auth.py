#!/usr/bin/env python3
"""
Component: Authentication

JWT-based auth for SurrealDB.
"""

import asyncio
import datetime
import jwt
from functools import wraps
from typing import Optional


SECRET_KEY = "your-secret-key-change-in-production"


class Auth:
    """JWT Authentication component."""
    
    def __init__(self, secret_key: str = SECRET_KEY, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, user_id: str, expires_in: int = 86400) -> str:
        """Create JWT token."""
        payload = {
            "sub": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in),
            "iat": datetime.datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode token."""
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def signin(self, db, username: str, password: str) -> dict:
        """Sign in and return token."""
        # In real app, verify against DB
        user = asyncio.run(db.query(
            "SELECT * FROM user WHERE email = $email",
            {"email": username}
        ))
        
        if not user or not user[0]:
            return {"error": "Invalid credentials"}
        
        token = self.create_token(user[0][0].get("id", username))
        return {"token": token, "user": user[0][0].get("id")}
    
    def signup(self, db, username: str, password: str, **kwargs) -> dict:
        """Sign up and return token."""
        # Hash password (in real app)
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        result = asyncio.run(db.query(
            "CREATE user SET email = $email, password = $pass",
            {"email": username, "pass": password_hash}
        ))
        
        if result and result[0]:
            token = self.create_token(result[0][0].get("id"))
            return {"token": token, "user": result[0][0].get("id")}
        
        return {"error": "Failed to create user"}


# Example middleware
def require_auth(auth: Auth):
    """Decorator to require auth."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return {"error": "No token"}
            
            token = auth_header.replace("Bearer ", "")
            payload = auth.verify_token(token)
            
            if not payload:
                return {"error": "Invalid token"}
            
            request["user_id"] = payload.get("sub")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


auth = Auth()


if __name__ == "__main__":
    # Test
    token = auth.create_token("user:alice")
    print(f"Token: {token[:50]}...")
    
    payload = auth.verify_token(token)
    print(f"Payload: {payload}")