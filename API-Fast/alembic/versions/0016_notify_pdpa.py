"""D3+D4: notification platform (LINE Messaging, templates, prefs, in-app) + PDPA.

Revision ID: 0016_notify_pdpa
Revises: 0015_devices_tenant
Create Date: 2026-11-07

* ``notification_template`` — per-event / locale / channel message bodies
* ``notification_preference`` — per-member channel + mute prefs (+ LINE user id)
* ``in_app_notification`` — notification-center inbox rows
* ``member`` consent version/text snapshot columns
* ``notification_outbox`` gains ``dead_lettered_at`` for dead-letter UI

Idempotent DDL (IF NOT EXISTS) so a legacy stamped DB can upgrade cleanly.
"""
from __future__ import annotations

from alembic import op

revision = "0016_notify_pdpa"
down_revision = "0015_devices_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_template (
            "templateId" UUID PRIMARY KEY,
            "companyId" UUID REFERENCES company("companyId") ON DELETE CASCADE,
            "eventKey" VARCHAR(80) NOT NULL,
            locale VARCHAR(10) NOT NULL DEFAULT 'th',
            channel VARCHAR(20) NOT NULL DEFAULT 'line',
            subject VARCHAR(255),
            "bodyTemplate" TEXT NOT NULL,
            "createdAt" TIMESTAMPTZ DEFAULT now(),
            "updatedAt" TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_template_scope
        ON notification_template ("companyId", "eventKey", locale, channel)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS notification_template_company_idx
        ON notification_template ("companyId", "eventKey")
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_preference (
            "preferenceId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "memberId" UUID NOT NULL REFERENCES member("memberId") ON DELETE CASCADE,
            "channelEmail" BOOLEAN NOT NULL DEFAULT true,
            "channelLine" BOOLEAN NOT NULL DEFAULT true,
            "channelInApp" BOOLEAN NOT NULL DEFAULT true,
            "lineUserId" VARCHAR(64),
            "mutedEvents" JSONB NOT NULL DEFAULT '[]'::jsonb,
            locale VARCHAR(10) NOT NULL DEFAULT 'th',
            "createdAt" TIMESTAMPTZ DEFAULT now(),
            "updatedAt" TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_preference_member
        ON notification_preference ("companyId", "memberId")
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS in_app_notification (
            "notificationId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "memberId" UUID NOT NULL REFERENCES member("memberId") ON DELETE CASCADE,
            event VARCHAR(80) NOT NULL,
            title VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            "readAt" TIMESTAMPTZ,
            "createdAt" TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS in_app_notification_member_created_idx
        ON in_app_notification ("memberId", "createdAt")
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS in_app_notification_company_unread_idx
        ON in_app_notification ("companyId", "memberId")
        """
    )

    op.execute(
        """
        ALTER TABLE member
            ADD COLUMN IF NOT EXISTS biometric_consent_version VARCHAR(40),
            ADD COLUMN IF NOT EXISTS biometric_consent_text TEXT
        """
    )

    op.execute(
        """
        ALTER TABLE notification_outbox
            ADD COLUMN IF NOT EXISTS "deadLetteredAt" TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS notification_outbox_dead_letter_idx
        ON notification_outbox (status, "deadLetteredAt")
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS notification_outbox_dead_letter_idx")
    op.execute(
        'ALTER TABLE notification_outbox DROP COLUMN IF EXISTS "deadLetteredAt"'
    )
    op.execute(
        "ALTER TABLE member DROP COLUMN IF EXISTS biometric_consent_text"
    )
    op.execute(
        "ALTER TABLE member DROP COLUMN IF EXISTS biometric_consent_version"
    )
    op.execute("DROP TABLE IF EXISTS in_app_notification")
    op.execute("DROP TABLE IF EXISTS notification_preference")
    op.execute("DROP TABLE IF EXISTS notification_template")
