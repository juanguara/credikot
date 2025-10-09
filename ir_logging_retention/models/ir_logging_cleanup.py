# -*- coding: utf-8 -*-
import logging
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PARAM_KEY = "credikot.ir_logging_retention_days"   # parámetro del sistema

class IrLoggingCleanup(models.AbstractModel):
    _name = "ir.logging.cleanup"
    _description = "Purge de ir.logging por retención (días)"

    @api.model
    def run_cleanup(self, dry_run=False, max_rows_per_batch=10000):
        """Elimina registros de ir_logging con create_date < (now - N días).
        - N leído de ir.config_parameter (PARAM_KEY).
        - Borrado por lotes con LIMIT para evitar locks prolongados.
        """
        ICP = self.env["ir.config_parameter"].sudo()

        # Leer parámetro N (días). Default 30.
        days_str = ICP.get_param(PARAM_KEY, default="30")
        try:
            days = int(days_str)
        except Exception:
            days = 30

        # Normalizar (0 => deshabilita, tope 3650 días = ~10 años)
        days = max(0, min(days, 3650))

        if days <= 0:
            _logger.info("ir_logging cleanup: retention=0 => SKIP")
            return {"status": "skipped", "reason": "retention=0"}

        # Umbral de fecha/hora (UTC). Se borra TODO lo anterior a este instante.
        threshold_dt = fields.Datetime.now() - relativedelta(days=days)

        cr = self._cr
        # Contar candidatos (solo informativo)
        cr.execute("SELECT count(1) FROM ir_logging WHERE create_date < %s", (threshold_dt,))
        total_candidates = cr.fetchone()[0]

        if dry_run:
            _logger.info("ir_logging cleanup (dry-run): %s candidatos (< %s)", total_candidates, threshold_dt)
            return {"status": "dry_run", "threshold": str(threshold_dt), "candidates": total_candidates}

        total_deleted = 0

        # Borrado en lotes usando subquery con LIMIT
        while True:
            cr.execute("""
                DELETE FROM ir_logging
                WHERE id IN (
                    SELECT id
                    FROM ir_logging
                    WHERE create_date < %s
                    ORDER BY id
                    LIMIT %s
                )
                RETURNING id
            """, (threshold_dt, max_rows_per_batch))
            deleted_ids = cr.fetchall()
            batch_deleted = len(deleted_ids)
            total_deleted += batch_deleted

            # Commit por lote grande para liberar locks
            if batch_deleted >= max_rows_per_batch:
                cr.commit()

            if batch_deleted < max_rows_per_batch:
                break

        _logger.info(
            "ir_logging cleanup: eliminados %s de %s registros anteriores a %s (retención=%s días)",
            total_deleted, total_candidates, threshold_dt, days
        )

        return {
            "status": "ok",
            "deleted": total_deleted,
            "candidates": total_candidates,
            "threshold": str(threshold_dt),
            "retention_days": days,
        }
