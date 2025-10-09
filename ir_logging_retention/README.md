# ir_logging_retention (Odoo 18)

Cron diario que elimina registros de `ir_logging` más antiguos que **N días**.
N se define con el parámetro del sistema `credikot.ir_logging_retention_days` (default 30).

**Odoo 18 cambia ir.cron:** se eliminaron campos `numbercall` y `doall`. Este módulo ya está adaptado.

## Instalación
1. Copiar el módulo en tu ruta de addons, por ejemplo:
   `/odoo/18/custom-addons/ir_logging_retention`
2. Actualizar la lista de aplicaciones e **instalar** el módulo.
3. Ajustar el parámetro en **Ajustes → Técnico → Parámetros del sistema** o desde **Ajustes** (bloque agregado):
   - Key: `credikot.ir_logging_retention_days`
   - Value: número de días (ej. `30`).
4. Revisar el cron en **Ajustes → Técnico → Automatizaciones → Acciones programadas**.

## Prueba (dry-run) desde shell
```python
env['ir.logging.cleanup'].run_cleanup(dry_run=True)
```

## Nota
Para instalaciones con mucho log, considerar un índice:
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ir_logging_create_date ON ir_logging (create_date);
```
