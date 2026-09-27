"""Endurecimiento (Fase 8): tablas de trazabilidad append-only garantizadas por la base de datos.

* ``ops.audit_logs`` y ``learning.student_state_history``: sin UPDATE ni DELETE.
* ``learning.interactions``: sin DELETE; UPDATE solo para completar una vez ``next_student_action`` y
  ``ai_interpretation`` (enriquecimientos posteriores al registro), nunca para cambiar lo ocurrido.

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION ops.forbid_modification() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'La tabla %.% es append-only: % no permitido', TG_TABLE_SCHEMA, TG_TABLE_NAME, TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION learning.guard_interaction_update() RETURNS trigger AS $$
        BEGIN
            IF (to_jsonb(NEW) - 'next_student_action' - 'ai_interpretation')
               IS DISTINCT FROM (to_jsonb(OLD) - 'next_student_action' - 'ai_interpretation') THEN
                RAISE EXCEPTION 'learning.interactions es append-only: solo se pueden completar next_student_action y ai_interpretation'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;
            IF OLD.next_student_action IS NOT NULL AND NEW.next_student_action IS DISTINCT FROM OLD.next_student_action THEN
                RAISE EXCEPTION 'next_student_action ya fue registrado' USING ERRCODE = 'insufficient_privilege';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for schema, table in (("ops", "audit_logs"), ("learning", "student_state_history")):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {schema}.{table} "
            "FOR EACH ROW EXECUTE FUNCTION ops.forbid_modification()"
        )
    op.execute(
        "CREATE TRIGGER trg_interactions_no_delete BEFORE DELETE ON learning.interactions "
        "FOR EACH ROW EXECUTE FUNCTION ops.forbid_modification()"
    )
    op.execute(
        "CREATE TRIGGER trg_interactions_guard_update BEFORE UPDATE ON learning.interactions "
        "FOR EACH ROW EXECUTE FUNCTION learning.guard_interaction_update()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_interactions_guard_update ON learning.interactions")
    op.execute("DROP TRIGGER IF EXISTS trg_interactions_no_delete ON learning.interactions")
    op.execute("DROP TRIGGER IF EXISTS trg_student_state_history_append_only ON learning.student_state_history")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON ops.audit_logs")
    op.execute("DROP FUNCTION IF EXISTS learning.guard_interaction_update()")
    op.execute("DROP FUNCTION IF EXISTS ops.forbid_modification()")
