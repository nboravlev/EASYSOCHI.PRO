"""add provider column and rename yk_payment_id to provider_payment_id

Платёжная система стала переключаемой (PAYMENT_PROVIDER в .env), поэтому по
записи в payments должно быть видно, каким провайдером она создана. Заодно
имя yk_payment_id перестало соответствовать содержимому: колонка давно хранит
InvId от Robokassa, а не идентификатор ЮKassa.

Уникальность переносится на пару (provider, provider_payment_id): InvId у
Robokassa — 32-битное число, id у ЮKassa — UUID, и глобальная уникальность
одного только идентификатора смысла не имеет.

Revision ID: a1b2c3d4e5f6
Revises: e4aadbd0d9f4
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e4aadbd0d9f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Колонка добавляется допускающей NULL, иначе ALTER упадёт на
    #    существующих строках.
    op.add_column('payments', sa.Column('provider', sa.String(length=20), nullable=True))

    # 2. Бэкфилл: всё, что уже есть в таблице, создано Robokassa.
    op.execute("UPDATE payments SET provider = 'robokassa' WHERE provider IS NULL")

    # 3. Теперь можно запретить NULL. server_default намеренно не ставим:
    #    провайдера всегда проставляет сервис, молчаливая подстановка значения
    #    скрыла бы ошибку в коде.
    op.alter_column('payments', 'provider', nullable=False)

    # 4. Переименование колонки. Индексы и ограничения Postgres переносит сам.
    op.alter_column('payments', 'yk_payment_id', new_column_name='provider_payment_id')

    # 5. Уникальность переезжает с одной колонки на пару.
    op.drop_constraint('payments_yk_payment_id_key', 'payments', type_='unique')
    op.create_unique_constraint(
        'uq_payments_provider_payment_id',
        'payments',
        ['provider', 'provider_payment_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_payments_provider_payment_id', 'payments', type_='unique')
    op.alter_column('payments', 'provider_payment_id', new_column_name='yk_payment_id')
    op.create_unique_constraint('payments_yk_payment_id_key', 'payments', ['yk_payment_id'])
    op.drop_column('payments', 'provider')
