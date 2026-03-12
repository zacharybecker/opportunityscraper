"""add search vector to opportunities

Revision ID: 0002_search_vector
Revises: 7766a591332c
Create Date: 2026-03-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_search_vector'
down_revision: Union[str, None] = '7766a591332c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tsvector column
    op.add_column('opportunities', sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True))

    # Create GIN index
    op.create_index('idx_opp_search', 'opportunities', ['search_vector'], postgresql_using='gin')

    # Create trigger function to auto-update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION opportunities_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.solicitation_number, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.agency, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trig_opp_search_vector
        BEFORE INSERT OR UPDATE OF title, solicitation_number, agency, description
        ON opportunities
        FOR EACH ROW
        EXECUTE FUNCTION opportunities_search_vector_update();
    """)

    # Backfill existing rows
    op.execute("""
        UPDATE opportunities SET search_vector =
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(solicitation_number, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(agency, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'C');
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trig_opp_search_vector ON opportunities;")
    op.execute("DROP FUNCTION IF EXISTS opportunities_search_vector_update();")
    op.drop_index('idx_opp_search', table_name='opportunities')
    op.drop_column('opportunities', 'search_vector')
