"""Initial migration

Revision ID: ae8894d915af
Revises: 
Create Date: 2025-02-01 02:18:22.758539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ae8894d915af'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('hadith_collections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('name_arabic', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('narrators',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('name_arabic', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('surahs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('name_arabic', sa.String(), nullable=True),
    sa.Column('is_makki', sa.Boolean(), nullable=True),
    sa.Column('verses_count', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('topics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('name_arabic', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('hadiths',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('collection_id', sa.Integer(), nullable=True),
    sa.Column('hadith_number', sa.Integer(), nullable=True),
    sa.Column('chapter_number', sa.Integer(), nullable=True),
    sa.Column('arabic', sa.String(), nullable=True),
    sa.Column('english', sa.String(), nullable=True),
    sa.Column('grading', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['collection_id'], ['hadith_collections.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('verses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('surah_id', sa.Integer(), nullable=True),
    sa.Column('verse_number', sa.Integer(), nullable=True),
    sa.Column('arabic', sa.String(), nullable=True),
    sa.Column('english', sa.String(), nullable=True),
    sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
    sa.ForeignKeyConstraint(['surah_id'], ['surahs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('hadith_narrators',
    sa.Column('hadith_id', sa.Integer(), nullable=True),
    sa.Column('narrator_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['hadith_id'], ['hadiths.id'], ),
    sa.ForeignKeyConstraint(['narrator_id'], ['narrators.id'], )
    )
    op.create_table('hadith_topics',
    sa.Column('hadith_id', sa.Integer(), nullable=True),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['hadith_id'], ['hadiths.id'], ),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], )
    )
    op.create_table('verse_topics',
    sa.Column('verse_id', sa.Integer(), nullable=True),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
    sa.ForeignKeyConstraint(['verse_id'], ['verses.id'], )
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('verse_topics')
    op.drop_table('hadith_topics')
    op.drop_table('hadith_narrators')
    op.drop_table('verses')
    op.drop_table('hadiths')
    op.drop_table('topics')
    op.drop_table('surahs')
    op.drop_table('narrators')
    op.drop_table('hadith_collections')
    # ### end Alembic commands ###
