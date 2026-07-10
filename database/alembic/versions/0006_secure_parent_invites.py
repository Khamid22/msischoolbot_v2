"""secure, single-use parent invite codes

Revision ID: 0006_secure_parent_invites
Revises: 0005_canonical_identity
Create Date: 2026-07-10
"""

from __future__ import annotations

import hashlib

from alembic import op
from sqlalchemy import text


revision = "0006_secure_parent_invites"
down_revision = "0005_canonical_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    invites = bind.execute(
        text("SELECT id, token_hash FROM msi_v2.account_invites ORDER BY id")
    ).mappings().all()
    for invite in invites:
        raw_code = str(invite["token_hash"] or "").strip()
        digest = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
        bind.execute(
            text(
                "UPDATE msi_v2.account_invites SET token_hash = :digest WHERE id = :invite_id"
            ),
            {"digest": digest, "invite_id": int(invite["id"])},
        )

    op.execute(
        """
        ALTER TABLE msi_v2.account_invites
        ADD COLUMN IF NOT EXISTS used_by_parent_id BIGINT
            REFERENCES msi_v2.parents(id) ON DELETE SET NULL;

        UPDATE msi_v2.account_invites
        SET status = 'expired'
        WHERE status = 'pending'
          AND expires_at IS NOT NULL
          AND expires_at <= now();

        UPDATE msi_v2.account_invites
        SET status = 'consumed'
        WHERE status = 'pending'
          AND used_count >= max_uses;

        ALTER TABLE msi_v2.account_invites DROP COLUMN IF EXISTS token;

        ALTER TABLE msi_v2.account_invites
        DROP CONSTRAINT IF EXISTS account_invites_usage_check;
        ALTER TABLE msi_v2.account_invites
        ADD CONSTRAINT account_invites_usage_check
        CHECK (max_uses > 0 AND used_count >= 0 AND used_count <= max_uses);

        CREATE INDEX IF NOT EXISTS idx_account_invites_status_expiry
        ON msi_v2.account_invites (status, expires_at)
        WHERE status = 'pending';
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "0006_secure_parent_invites is intentionally irreversible: plaintext invite "
        "payloads were deleted. Restore from a pre-0006 backup or regenerate invites."
    )
