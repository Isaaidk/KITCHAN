"""Crear tabla pedidos

Revision ID: 93af7d78ccc0
Revises: 6d964f82bbbd
Create Date: 2026-09-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "93af7d78ccc0"
down_revision: Union[str, None] = "6d964f82bbbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pedidos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("restaurante_id", sa.UUID(), nullable=False),
        sa.Column("origen", sa.String(length=30), nullable=False),
        sa.Column("id_externo", sa.String(length=100), nullable=True),
        sa.Column("cliente", sa.String(length=150), nullable=False),
        sa.Column("nota_cliente", sa.String(length=500), nullable=True),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "NUEVA",
                "EN_PREPARACION",
                "LISTA",
                "ENTREGADA",
                "CANCELADA",
                name="estado_pedido_enum",
            ),
            nullable=False,
        ),
        sa.Column("estado_entrega", sa.String(length=50), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurante_id"], ["restaurantes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pedidos_id"), "pedidos", ["id"], unique=False)
    op.create_index(
        op.f("ix_pedidos_restaurante_id"), "pedidos", ["restaurante_id"], unique=False
    )
    op.create_index(
        op.f("ix_pedidos_id_externo"), "pedidos", ["id_externo"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pedidos_id_externo"), table_name="pedidos")
    op.drop_index(op.f("ix_pedidos_restaurante_id"), table_name="pedidos")
    op.drop_index(op.f("ix_pedidos_id"), table_name="pedidos")
    op.drop_table("pedidos")
    sa.Enum(name="estado_pedido_enum").drop(op.get_bind(), checkfirst=True)
