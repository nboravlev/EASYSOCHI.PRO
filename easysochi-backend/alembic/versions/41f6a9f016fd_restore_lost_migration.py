from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '41f6a9f016fd'
down_revision = None   # <=== Если ты точно не знаешь предыдущую
branch_labels = None
depends_on = None

def upgrade():
    pass   # таблица уже существует в БД

def downgrade():
    pass
