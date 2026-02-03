"""Backward compatibility alias for Tenant.

The system now uses `Company` as the primary model. This module keeps
the previous import path (`Tenant`) available to avoid breaking existing
imports while the codebase migrates.
"""

from app.models.company import Company


# Alias to preserve old imports
Tenant = Company
