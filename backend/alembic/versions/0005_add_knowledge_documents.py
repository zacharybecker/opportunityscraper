"""add knowledge documents

Revision ID: 0005_knowledge
Revises: 0004_in_app_notifs
Create Date: 2026-03-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0005_knowledge'
down_revision: Union[str, None] = '0004_in_app_notifs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('knowledge_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('doc_type', sa.String(20), nullable=False, server_default='text'),
        sa.Column('file_path', sa.String(2048), nullable=True),
        sa.Column('original_filename', sa.String(500), nullable=True),
        sa.Column('url', sa.String(2048), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('category', sa.String(50), server_default='general'),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('uploaded_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['company_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_kb_search', 'knowledge_documents', ['search_vector'], postgresql_using='gin')

    # Create trigger for knowledge documents search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION kb_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.extracted_text, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trig_kb_search_vector
        BEFORE INSERT OR UPDATE OF title, extracted_text
        ON knowledge_documents
        FOR EACH ROW
        EXECUTE FUNCTION kb_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trig_kb_search_vector ON knowledge_documents;")
    op.execute("DROP FUNCTION IF EXISTS kb_search_vector_update();")
    op.drop_index('idx_kb_search', table_name='knowledge_documents')
    op.drop_table('knowledge_documents')
