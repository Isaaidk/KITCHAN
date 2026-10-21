"""Pedidos: método de pago y momentos de cocina

Agrega a `pedidos`:
- metodo_pago: cómo se pagó (EFECTIVO, TARJETA, ...); NULL si el canal no lo informa.
- fecha_aceptacion / fecha_lista: cuándo la cocina empezó y terminó el pedido,
  para calcular el tiempo de preparación real en las analíticas.

Revision ID: c4a1d8e5b2f7
Revises: b7f3c2a9d4e1
Create Date: 2026-10-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4a1d8e5b2f7"
down_revision: Union[str, None] = "b7f3c2a9d4e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pedidos", sa.Column("metodo_pago", sa.String(length=30), nullable=True))
    op.add_column(
        "pedidos", sa.Column("fecha_aceptacion", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "pedidos", sa.Column("fecha_lista", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("pedidos", "fecha_lista")
    op.drop_column("pedidos", "fecha_aceptacion")
    op.drop_column("pedidos", "metodo_pago")
