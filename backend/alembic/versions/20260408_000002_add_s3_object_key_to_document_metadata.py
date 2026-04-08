"""add s3 object key to document metadata

Revision ID: 20260408_000002
Revises: 20260407_000001
Create Date: 2026-04-08 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_000002"
down_revision = "20260407_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_metadata", sa.Column("s3_object_key", sa.String(length=1024), nullable=True))
    op.execute("UPDATE document_metadata SET s3_object_key = CONCAT('legacy/', id::text, '-', filename)")
    op.alter_column("document_metadata", "s3_object_key", nullable=False)
    op.create_unique_constraint("uq_document_metadata_s3_object_key", "document_metadata", ["s3_object_key"])


def downgrade() -> None:
    op.drop_constraint("uq_document_metadata_s3_object_key", "document_metadata", type_="unique")
    op.drop_column("document_metadata", "s3_object_key")
