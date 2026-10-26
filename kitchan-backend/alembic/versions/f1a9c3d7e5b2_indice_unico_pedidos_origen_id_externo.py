"""Indice unico de pedidos por plataforma e id externo

Revision ID: f1a9c3d7e5b2
Revises: e7f3c1a8b4d2
Create Date: 2026-10-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a9c3d7e5b2"
down_revision: Union[str, None] = "e7f3c1a8b4d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDICE = "uq_pedidos_origen_id_externo"


def upgrade() -> None:
    conexion = op.get_bind()
    duplicados = conexion.execute(
        sa.text(
            "SELECT origen, id_externo, COUNT(*) AS cantidad FROM pedidos "
            "WHERE id_externo IS NOT NULL "
            "GROUP BY origen, id_externo HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if duplicados:
        detalle = ", ".join(
            f"{d.origen} {d.id_externo} (x{d.cantidad})" for d in duplicados
        )
        raise RuntimeError(
            "No se puede crear el indice unico: hay pedidos duplicados por "
            f"plataforma e id externo. Resuelvelos primero: {detalle}"
        )

    op.create_index(
        INDICE,
        "pedidos",
        ["origen", "id_externo"],
        unique=True,
        postgresql_where=sa.text("id_externo IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(INDICE, table_name="pedidos")
