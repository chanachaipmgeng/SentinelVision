"""F2: widen sentinel_access_zone.relay_secret for Fernet sealing.

Revision ID: 0019_sentinel_relay_secret
Revises: 0018_sentinel_incident_lifecycle
Create Date: 2026-11-08

Owned by branch ``feat/phase-f-relay-search``.

**Dependency:** F1 owns ``0018_sentinel_incident_lifecycle``. That revision is
not on this branch; Phase F integration must merge Branch A (F1) before applying
this revision so the Alembic graph stays linear (0017 → 0018 → 0019).

Column was VARCHAR(128); Fernet tokens with the ``fernet:`` prefix need more
headroom (VARCHAR(512)). Application code seals plaintext on zone create/update
via ``outbox_crypto.seal_relay_secret`` and decrypts only at relay dispatch.
"""
from __future__ import annotations

from alembic import op

revision = "0019_sentinel_relay_secret"
# F1 Branch A — absent on this feature branch until Phase F integration.
down_revision = "0018_sentinel_incident_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sentinel_access_zone
        ALTER COLUMN relay_secret TYPE VARCHAR(512)
        """
    )


def downgrade() -> None:
    # Truncation risk if sealed values exceed 128; safe only when secrets are short/plaintext.
    op.execute(
        """
        ALTER TABLE sentinel_access_zone
        ALTER COLUMN relay_secret TYPE VARCHAR(128)
        """
    )
