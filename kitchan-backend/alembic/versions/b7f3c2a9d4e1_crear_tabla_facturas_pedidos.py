"""Crear tabla facturas_pedidos

Revision ID: b7f3c2a9d4e1
Revises: 93af7d78ccc0
Create Date: 2026-10-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f3c2a9d4e1"
down_revision: Union[str, None] = "93af7d78ccc0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "facturas_pedidos",
        sa.Column("pedido_id", sa.UUID(), nullable=False),
        sa.Column("restaurante_id", sa.UUID(), nullable=False),
        sa.Column("odoo_move_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.String(length=64), nullable=True),
        sa.Column(
            "estado",
            sa.Enum(
                "PENDIENTE_SRI",
                "AUTORIZADA",
                "CON_ERROR",
                "ANULADA",
                name="estado_factura_enum",
            ),
            nullable=False,
        ),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("numero_autorizacion", sa.String(length=64), nullable=True),
        sa.Column("fecha_autorizacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mensaje_error", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("pedido_id"),
        sa.UniqueConstraint("odoo_move_id"),
    )
    op.create_index(
        op.f("ix_facturas_pedidos_restaurante_id"),
        "facturas_pedidos",
        ["restaurante_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_facturas_pedidos_estado"), "facturas_pedidos", ["estado"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_facturas_pedidos_estado"), table_name="facturas_pedidos")
    op.drop_index(
        op.f("ix_facturas_pedidos_restaurante_id"), table_name="facturas_pedidos"
    )
    op.drop_table("facturas_pedidos")
    sa.Enum(name="estado_factura_enum").drop(op.get_bind(), checkfirst=True)
