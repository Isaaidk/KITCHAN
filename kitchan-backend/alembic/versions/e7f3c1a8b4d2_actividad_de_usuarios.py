"""Actividad de usuarios

- usuarios.creado_en: fecha de alta (las filas existentes toman la fecha de la migración).
- usuarios.ultimo_acceso: último inicio de sesión (NULL si nunca ha entrado).
- pedidos.aceptado_por_id: usuario de KITCHAN que aceptó el pedido, para medir
  la actividad de cada operador.

Revision ID: e7f3c1a8b4d2
Revises: d6e2b9f1a3c8
Create Date: 2026-10-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f3c1a8b4d2"
down_revision: Union[str, None] = "d6e2b9f1a3c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pedidos", sa.Column("aceptado_por_id", sa.String(length=36), nullable=True)
    )
    op.create_index("ix_pedidos_aceptado_por_id", "pedidos", ["aceptado_por_id"])


def downgrade() -> None:
    op.drop_index("ix_pedidos_aceptado_por_id", table_name="pedidos")
    op.drop_column("pedidos", "aceptado_por_id")
    op.drop_column("usuarios", "ultimo_acceso")
    op.drop_column("usuarios", "creado_en")
