"""Códigos de recuperación de contraseña

Tabla `codigos_recuperacion`: códigos de 6 dígitos (solo su hash) que se envían
por correo para restablecer la contraseña. Vencen, limitan intentos y son de un
solo uso.

Revision ID: d6e2b9f1a3c8
Revises: c4a1d8e5b2f7
Create Date: 2026-10-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6e2b9f1a3c8"
down_revision: Union[str, None] = "c4a1d8e5b2f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "codigos_recuperacion",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("codigo_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_codigos_recuperacion_usuario_id", "codigos_recuperacion", ["usuario_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_codigos_recuperacion_usuario_id", table_name="codigos_recuperacion"
    )
    op.drop_table("codigos_recuperacion")
