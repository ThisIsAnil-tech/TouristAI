"""Initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-27 23:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables are dynamically managed by Base.metadata.create_all on startup
    pass


def downgrade() -> None:
    pass
