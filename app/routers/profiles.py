"""
Profiles router — Phase 2.

Endpoints:
  GET  /profiles                    — list all available company profiles
  GET  /profiles/{profile_id}       — retrieve a specific profile's full configuration
"""

from fastapi import APIRouter, HTTPException
from app.models.profile import CompanyProfile
from app.services.profile_registry import get_profile, list_profiles

router = APIRouter()


@router.get("", response_model=list[CompanyProfile])
def get_all_profiles():
    """Return all registered company profiles."""
    return list_profiles()


@router.get("/{profile_id}", response_model=CompanyProfile)
def get_profile_by_id(profile_id: str):
    """Return a specific profile by ID (e.g. 'fintech', 'saas_startup', 'default')."""
    try:
        return get_profile(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
