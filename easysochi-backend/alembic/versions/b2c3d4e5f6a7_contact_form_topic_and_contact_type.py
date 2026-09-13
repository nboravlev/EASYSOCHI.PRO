"""contact_form: add contact_type, topic, source and rename email to contact_value

Форма обратной связи научилась принимать не только почту, но и телефон или
ник в Telegram, а также тему обращения и страницу, с которой отправлена.

Колонка email переименована в contact_value: она давно перестала быть про
почту. Существующие записи заполняются contact_type='email' — всё, что
лежало в таблице до сих пор, приходило именно через поле email.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Новые колонки добавляются допускающими NULL, иначе ALTER упал бы на
    # существующих строках, и только потом получают NOT NULL.
    op.add_column('contact_form', sa.Column('contact_type', sa.String(length=20), nullable=True))
    op.add_column('contact_form', sa.Column('topic', sa.String(length=100), nullable=True))

    # source остаётся nullable: у старых записей источник неизвестен, и
    # выдумывать его значение нечестно.
    op.add_column('contact_form', sa.Column('source', sa.String(length=200), nullable=True))

    op.execute("UPDATE contact_form SET contact_type = 'email' WHERE contact_type IS NULL")
    op.execute("UPDATE contact_form SET topic = 'Другое' WHERE topic IS NULL")

    op.alter_column('contact_form', 'contact_type', nullable=False)
    op.alter_column('contact_form', 'topic', nullable=False)

    op.alter_column('contact_form', 'email', new_column_name='contact_value')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('contact_form', 'contact_value', new_column_name='email')
    op.drop_column('contact_form', 'source')
    op.drop_column('contact_form', 'topic')
    op.drop_column('contact_form', 'contact_type')
