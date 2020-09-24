# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Order Point Method:
#    - Order if the virtual stock of today is below the min of the defined order point
#

from odoo import api, models, tools, fields

import logging
import threading

_logger = logging.getLogger(__name__)


class StockSchedulerCompute(models.TransientModel):
    _name = 'stock.scheduler.compute'
    _description = 'Run Scheduler Manually'

    def _procure_calculation_orderpoint(self):
        with api.Environment.manage():
            # As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            scheduler_cron = self.sudo().env.ref('stock.ir_cron_scheduler_action')
            # Avoid to run the scheduler multiple times in the same time
            try:
                with tools.mute_logger('odoo.sql_db'):
                    self._cr.execute("SELECT id FROM ir_cron WHERE id = %s FOR UPDATE NOWAIT", (scheduler_cron.id,))
            except Exception:
                _logger.info('Attempt to run procurement scheduler aborted, as already running')
                self._cr.rollback()
                self._cr.close()
                return {}

            times = []
            for company in self.env.user.company_ids:
                start = fields.Datetime.now()
                print("-------------> STARTING Scheduler for company: " + str(company.id) + " at time: " + str(fields.Datetime.now()))
                cids = (self.env.user.company_id | self.env.user.company_ids).ids
                self.env['procurement.group'].with_context(allowed_company_ids=cids).run_scheduler(
                    use_new_cursor=self._cr.dbname,
                    company_id=company.id)
                delta = fields.Datetime.now() - start
                print("-------------> FINISHED Scheduler for company: " + str(company.id) + " at time: " + str(fields.Datetime.now()))
                print(company.id, delta.total_seconds())
                times.append("%s\t%s" % (company.id, delta.total_seconds()))
            print("\n".join(times))
            new_cr.close()
            return {}

    def procure_calculation(self):
        threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint, args=())
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
