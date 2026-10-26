"""Pedidos: teléfono, tipo de entrega y dirección

Agrega a `pedidos` los datos de contacto y entrega que informan canales como
WhatsApp. Todos son NULL cuando el canal no los da (nunca se inventan).

Revision ID: a3c5e7f9b1d2
Revises: f1a9c3d7e5b2
Create Date: 2026-10-26 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c5e7f9b1d2"
down_revision: Union[str, None] = "f1a9c3d7e5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pedidos", sa.Column("telefono_cliente", sa.String(length=30), nullable=True)
    )
    op.add_column(
        "pedidos", sa.Column("tipo_entrega", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "pedidos", sa.Column("direccion_entrega", sa.String(length=300), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("pedidos", "direccion_entrega")
    op.drop_column("pedidos", "tipo_entrega")
    op.drop_column("pedidos", "telefono_cliente")
