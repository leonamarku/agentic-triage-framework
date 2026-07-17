"""
Profile Registry — loads CompanyProfile objects from JSON files and serves
them by ID. Built-in profiles are always available; additional profiles can
be placed in the profiles/ directory and loaded at startup.

Phase 2 addition.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path

from app.models.profile import CompanyProfile, DEFAULT_PROFILE

logger = logging.getLogger(__name__)

_registry: dict[str, CompanyProfile] = {}


def init_profiles(profiles_dir: str = "profiles") -> None:
    """
    Load all JSON profile files from profiles_dir into the registry.
    Called once at application startup.
    """
    global _registry

    # Always register the default profile
    _registry[DEFAULT_PROFILE.id] = DEFAULT_PROFILE

    path = Path(profiles_dir)
    if not path.exists():
        logger.warning("Profiles directory '%s' not found — using default profile only.", profiles_dir)
        return

    loaded = 0
    for json_file in sorted(path.glob("*.json")):
        try:
            data = json.loads(json_file.read_text())
            profile = CompanyProfile(**data)
            _registry[profile.id] = profile
            loaded += 1
            logger.info("Loaded profile: %s (%s)", profile.id, profile.name)
        except Exception as e:
            logger.error("Failed to load profile from %s: %s", json_file, e)

    logger.info("Profile registry ready: %d profiles loaded.", len(_registry))


def get_profile(profile_id: str) -> CompanyProfile:
    """
    Return a profile by ID.
    Returns the default profile if profile_id is None or not found.
    """
    if not _registry:
        raise RuntimeError("Profile registry not initialised. Call init_profiles() at startup.")

    if profile_id is None:
        return _registry[DEFAULT_PROFILE.id]

    profile = _registry.get(profile_id)
    if profile is None:
        available = list(_registry.keys())
        raise ValueError(
            f"Profile '{profile_id}' not found. "
            f"Available profiles: {available}"
        )
    return profile


def list_profiles() -> list[CompanyProfile]:
    """Return all registered profiles."""
    if not _registry:
        raise RuntimeError("Profile registry not initialised.")
    return list(_registry.values())


def registry_ready() -> bool:
    return bool(_registry)
