from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
import json
import httpx
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import base64
from app.models import User
from app.helpers.database import get_db
from app.helpers.secrets import Secrets

logger = logging.getLogger(__name__)

ALGORITHMS = ["RS256"]
token_auth_scheme = HTTPBearer()


def ensure_bytes(key):
    if isinstance(key, str):
        key = key.encode("utf-8")
    return key


def decode_value(val):
    decoded = base64.urlsafe_b64decode(ensure_bytes(val + "=" * (4 - len(val) % 4)))
    return int.from_bytes(decoded, "big")


def rsa_pem_from_jwk(jwk):
    return (
        RSAPublicNumbers(n=decode_value(jwk["n"]), e=decode_value(jwk["e"]))
        .public_key(default_backend())
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


async def get_jwks():
    secrets = Secrets()
    auth0_issuer_url: str = f"https://{secrets.Auth0Domain}/"
    jwks_uri: str = f"{auth0_issuer_url}.well-known/jwks.json"

    logger.debug(f"Fetching JWKS from: {jwks_uri}")
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_uri)
        jwks = response.json()
        logger.debug(f"Received JWKS: {json.dumps(jwks, indent=2)}")
        return jwks


async def get_signing_key(token):
    jwks = await get_jwks()
    try:
        header = jwt.get_unverified_header(token)
        logger.debug(f"Token header: {header}")

        for key in jwks["keys"]:
            if key["kid"] == header["kid"]:
                logger.debug(f"Found matching key: {key['kid']}")
                if key["kty"] == "RSA":
                    return rsa_pem_from_jwk(key)

        logger.error(f"No matching key found. Token kid: {header['kid']}")
        raise HTTPException(status_code=401, detail="No matching key found")
    except Exception as e:
        logger.error(f"Error getting signing key: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def validate_jwt(token):
    secrets = Secrets()
    auth0_issuer_url: str = f"https://{secrets.Auth0Domain}/"
    auth0_audience: str = secrets.Auth0Audience

    logger.debug(f"Validating JWT with issuer: {auth0_issuer_url}")
    logger.debug(f"Audience: {auth0_audience}")

    try:
        signing_key = await get_signing_key(token)
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=ALGORITHMS,
            audience=auth0_audience,
            issuer=auth0_issuer_url,
        )
        return payload
    except JWTError as e:
        logger.error(f"Error validating JWT: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_authenticated_user(
    request: Request,
    token: HTTPBearer = Depends(token_auth_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = await validate_jwt(token.credentials)
        sub = payload["sub"]

        # Check if user exists, create if not
        db_user = db.query(User).filter(User.sub == sub).first()
        if not db_user:
            db_user = User(sub=sub)
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            from app.helpers.sandbox import sandbox_enabled, seed_user

            if sandbox_enabled():
                seed_user(db, db_user.id)

        user = {
            "sub": sub,
            "token": token.credentials,
        }
        request.session["user"] = user
        return user
    except JWTError as e:
        logger.error(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
