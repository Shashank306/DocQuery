# security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
import re
from app.core.config import settings
from app.core.logging_simple import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class PasswordValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

def validate_password(password: str) -> None:
    """Validate password according to security policy."""
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise PasswordValidationError(
            f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long"
        )
    
    if settings.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        raise PasswordValidationError("Password must contain at least one uppercase letter")
    
    if settings.REQUIRE_NUMBERS and not re.search(r'\d', password):
        raise PasswordValidationError("Password must contain at least one number")
    
    if settings.REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise PasswordValidationError("Password must contain at least one special character")

def hash_password(password: str) -> str:
    """Hash a plain password."""
    validate_password(password)
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token"
        )

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Refresh token creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create refresh token"
        )

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check if token has expired
        exp = payload.get("exp")
        if exp is None:
            raise AuthenticationError("Token missing expiration")
        
        if datetime.now(timezone.utc) > datetime.fromtimestamp(exp, tz=timezone.utc):
            raise AuthenticationError("Token has expired")
        
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise AuthenticationError("Token validation failed")

def extract_token_from_credentials(credentials: HTTPAuthorizationCredentials) -> str:
    """Extract token from HTTP authorization credentials."""
    if not credentials:
        raise AuthenticationError("Missing authorization header")
    
    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Invalid authentication scheme")
    
    return credentials.credentials

def get_password_hash(password: str) -> str:
    """Hash a password for storing in the database."""
    return pwd_context.hash(password)
