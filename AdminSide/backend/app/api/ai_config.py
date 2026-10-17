import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx
from pydantic import BaseModel

from typing import Literal

class ValidateResponse(BaseModel):
    status: Literal["valid", "invalid", "temporary_failure", "rate_limited", "none"]
    message: str

from app.api.dependencies import get_db, CurrentTenant, require_permission
from app.models.tenant_ai_config import TenantAiConfig
from app.schemas.ai_config import AiConfigResponse, AiConfigUpdate
from app.services.credential_service import get_credential_service

router = APIRouter(prefix="/ai-config", tags=["ai-config"])

@router.get("", response_model=AiConfigResponse)
def get_ai_config(
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    _ = Depends(require_permission("tenant:update")),
):
    """Get the current AI configuration for the tenant."""
    config = db.query(TenantAiConfig).filter(TenantAiConfig.tenant_id == tenant.id).first()
    
    if not config:
        # Return default state if no row exists
        return AiConfigResponse(
            provider="platform",
            model="gpt-4o",
            has_api_key=False,
            is_verified=False
        )
        
    return AiConfigResponse(
        provider=config.provider,
        model=config.model,
        has_api_key=bool(config.api_key_encrypted),
        is_verified=config.is_verified,
    )


@router.put("", response_model=AiConfigResponse)
def update_ai_config(
    payload: AiConfigUpdate,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    _ = Depends(require_permission("tenant:update")),
):
    """Update the AI configuration for the tenant."""
    if payload.provider not in ["platform", "openai"]:
        raise HTTPException(status_code=400, detail="Invalid provider")
    if payload.model not in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]:
        raise HTTPException(status_code=400, detail="Invalid model")
        
    config = db.query(TenantAiConfig).filter(TenantAiConfig.tenant_id == tenant.id).first()
    
    if not config:
        config = TenantAiConfig(tenant_id=tenant.id)
        db.add(config)
        
    config.provider = payload.provider
    config.model = payload.model
    
    # Process API key
    if payload.api_key:
        # Encrypt and save the new key
        try:
            credential_service = get_credential_service()
            config.api_key_encrypted = credential_service.encrypt(payload.api_key)
            config.is_verified = False
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to encrypt API key. Encryption may not be configured.")
    elif payload.api_key == "":
        # If explicitly passed as empty string, clear the key
        config.api_key_encrypted = None
        config.is_verified = False
        
    db.commit()
    
    return AiConfigResponse(
        provider=config.provider,
        model=config.model,
        has_api_key=bool(config.api_key_encrypted),
        is_verified=config.is_verified,
    )

@router.post("/validate", response_model=ValidateResponse)
def validate_ai_config(
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    _ = Depends(require_permission("tenant:update")),
):
    """Validate the stored OpenAI API key against the provider."""
    config = db.query(TenantAiConfig).filter(TenantAiConfig.tenant_id == tenant.id).first()
    if not config or not config.api_key_encrypted:
        return ValidateResponse(status="none", message="No API key configured.")
        
    try:
        credential_service = get_credential_service()
        api_key = credential_service.decrypt(config.api_key_encrypted)
    except Exception:
        return ValidateResponse(status="invalid", message="Stored credential could not be decrypted.")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
        
        if response.status_code == 200:
            config.is_verified = True
            db.commit()
            return ValidateResponse(status="valid", message="Configuration is valid.")
        
        if response.status_code == 401:
            config.is_verified = False
            db.commit()
            return ValidateResponse(status="invalid", message="Invalid credentials.")
            
        if response.status_code == 429:
            try:
                data = response.json()
                if "error" in data and isinstance(data["error"], dict) and data["error"].get("code") == "insufficient_quota":
                    return ValidateResponse(status="rate_limited", message="Provider quota/billing restriction; verification could not be completed.")
            except Exception:
                pass
            return ValidateResponse(status="rate_limited", message="Provider rate limit or quota restriction; verification could not be completed.")
            
        return ValidateResponse(status="temporary_failure", message=f"Provider returned error (status {response.status_code}).")
            
    except httpx.TimeoutException:
        return ValidateResponse(status="temporary_failure", message="Connection to provider timed out.")
    except httpx.RequestError:
        return ValidateResponse(status="temporary_failure", message="Network error connecting to provider.")
    except Exception:
        return ValidateResponse(status="temporary_failure", message="An unexpected error occurred during validation.")
