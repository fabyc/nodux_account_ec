#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.transaction import Transaction
from trytond.report import Report

__all__ = ['TaxesByPeriod', 'TaxesByPeriodStart',
        'PrintTaxesByPeriod']

class TaxesByPeriodStart(ModelView):
    'Taxes By Period Start'
    __name__ = 'nodux_account_ec.print_taxes_by_period.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ], depends=['fiscalyear', 'end_period'], required=True)
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        depends=['fiscalyear', 'start_period'], required=True)
    company = fields.Many2One('company.company', 'Company', required=True)

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
        }


class PrintTaxesByPeriod(Wizard):
    'Print Taxes By Period'
    __name__ = 'nodux_account_ec.print_taxes_by_period'
    start = StateView('nodux_account_ec.print_taxes_by_period.start',
        'nodux_account_ec.print_taxes_by_period_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('nodux_account_ec.report_taxes_by_period')

    def do_print_(self, action):
        start_period = self.start.start_period.id
        end_period = self.start.end_period.id

        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'start_period': start_period,
            'end_period': end_period,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class TaxesByPeriod(Report):
    __name__ = 'nodux_account_ec.taxes_by_period_report'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Period = pool.get('account.period')
        Company = pool.get('company.company')
        FiscalYear = pool.get('account.fiscalyear')
        Invoice = pool.get('account.invoice')
        company = Company(data['company'])

        start_period = Period(data['start_period'])
        end_period = Period(data['end_period'])

        dom_invoices = []
        dom_invoices.append([
            ('invoice_date', '>=', start_period.start_date),
            ('invoice_date', '<=', end_period.end_date),
            ('state', '!=', 'cancel'),
            ])

        invoices = Invoice.search(dom_invoices)

        taxes = {}
        for invoice in invoices:
            for itax in invoice.taxes:
                tax_id = itax.tax.id
                if tax_id not in taxes.keys():
                    taxes[tax_id] = {
                            'name': (itax.account.code or '') + ' - ' + itax.account.name,
                            'lines': [],
                            'sum_base': [],
                            'sum_amount': [],
                            }
                taxes[tax_id]['lines'].append(itax)
                taxes[tax_id]['sum_base'].append(itax.base)
                taxes[tax_id]['sum_amount'].append(itax.amount)
        objects = taxes.values()
        localcontext['start_period'] = start_period.name
        localcontext['end_period'] = end_period.name
        localcontext['company'] = company.party.name
        localcontext['fiscalyear'] = FiscalYear(data['fiscalyear']).name
        return super(TaxesByPeriod, cls).parse(report, objects, data,
            localcontext)
