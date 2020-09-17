# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from dateutil.relativedelta import relativedelta

class ContractHistory(models.Model):
    _name = 'hr.contract.history'
    _description = 'Contract history'
    _auto = False

    name = fields.Char('Contract Reference', readonly=True)
    date_hired = fields.Date('Hire Date', readonly=True)
    date_start = fields.Date('Start Date', readonly=True)
    date_end = fields.Date('End Date', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    # Not a related (join used in init query...), otherwise it cannot be used in _order
    employee_name = fields.Char('Employee name', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type", readonly=True)
    hr_responsible_id = fields.Many2one('res.users', string='HR Responsible', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Position', readonly=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True)
    resource_calendar_id = fields.Many2one('resource.calendar', readonly=True)
    wage = fields.Monetary('Wage', help="Employee's monthly gross wage.", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True)
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type", readonly=True)
    contract_ids = fields.One2many('hr.contract', string='Contracts', compute='_compute_contract_ids', readonly=True)
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')
    ], string='Kanban State', readonly=True)

    @api.model
    def _get_fields(self):
        return ','.join('hr_contract.%s' % name for name, field in self._fields.items()
                        if field.store and field.type not in ['many2many', 'one2many', 'related']
                                       and field.name not in ['date_hired', 'employee_name'])

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Reference contract is the currently open contract or, if none exists, the one with the latest start_date
        # that will be selected.
        # TODO validate contract selection (when no open is available, this is the contract with the latest date_start
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            WITH reference_contract AS (
                SELECT DISTINCT employee_id,
                                FIRST_VALUE(id) OVER w_partition AS id
                FROM hr_contract AS contract
                WHERE contract.state <> 'cancel'
                WINDOW w_partition AS (
                    PARTITION BY contract.employee_id
                    ORDER BY contract.date_start DESC
                    RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                )
            )
            SELECT employee.first_contract_date AS date_hired, COALESCE(employee.name,'') AS employee_name, %s
            FROM hr_contract
            INNER JOIN reference_contract USING (id)
            LEFT JOIN hr_employee AS employee ON reference_contract.employee_id = employee.id
        );""" % (self._table, self._get_fields()))

    @api.depends('employee_id.contract_ids')
    def _compute_contract_ids(self):
        # Optimising number of queries in case of multi
        contracts = self.env['hr.contract'].search(
            ['&',
             ('state', '!=', 'cancel'),
             ('id', 'in', [contract.id for employee in self.mapped('employee_id') for contract in employee.contract_ids])],
            order='date_start desc'
        )
        contract_history_dic = {contract_history.employee_id: contract_history for contract_history in self}

        for contract in contracts:
            contract_history_dic[contract.employee_id].contract_ids += contract
