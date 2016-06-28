#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from decimal import Decimal
from datetime import date
import operator
from sql.aggregate import Sum
from itertools import izip, groupby
from collections import OrderedDict
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.report import Report
from trytond.pyson import Eval, PYSONEncoder
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.modules.company import CompanyReport
import pytz
from datetime import datetime,timedelta

__all__ = ['AuxiliaryBookStart', 'PrintAuxiliaryBook', 'AuxiliaryBook',
        'PortfolioByPartyDetailed', 'TrialBalanceDetailed',
        'PrintTrialBalanceDetailed', 'PrintTrialBalanceDetailedStart',
        'PrintAuxiliaryParty', 'AuxiliaryParty', 'AuxiliaryPartyStart',
        'PrintTrialBalanceStart', 'PrintTrialBalance', 'TrialBalance',
        'OpenCashflowStatement', 'Cashflow', 'BalanceSheet', 'IncomeStatement',
        'CashflowTemplate', 'OpenCashflowStart', 'Account',
        'PrintPartyWithholding', 'PartyWithholdingStart',
        'PartyWithholding', 'OpenAgedBalanceStart', 'OpenAgedBalance',
        'AgedBalance','CashFlowStatement', 'TotalAnaliticCost', 'OpenAnalitic',
        'OpenCostAnalitic', 'OpenTotalSale', 'TotalSale', 'TotalSaleReport']

def fmt_acc(val):
    # Format account number function
    fmt = '%s' + '0' * (8 - len(str(val)))
    account_code_fmt = int(fmt % val)
    return account_code_fmt

class Account:
    __metaclass__ = PoolMeta
    __name__ = 'account.account'
    cashflow = fields.Many2One('account.account.cashflow', 'Cashflow',
        ondelete="RESTRICT", states={
            'invisible': Eval('kind') == 'view',
            },
        domain=[
            ('company', '=', Eval('company')),
            ], depends=['kind', 'company'])

class AuxiliaryBookStart(ModelView):
    'Auxiliary Book Start'
    __name__ = 'nodux_account_ec.print_auxiliary_book.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ], depends=['fiscalyear', 'end_period'])
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        depends=['fiscalyear', 'start_period'])
    start_account = fields.Many2One('account.account', 'Start Account',
            domain=[
                ('kind', '!=', 'view'),
                ('code', '!=', None),
            ])
    end_account = fields.Many2One('account.account', 'End Account',
            domain=[
                ('kind', '!=', 'view'),
                ('code', '!=', None),
            ])
    party = fields.Many2One('party.party', 'Party')
    company = fields.Many2One('company.company', 'Company', required=True)
    posted = fields.Boolean('Posted Move', help='Show only posted move')
    empty_account = fields.Boolean('Empty Account',
            help='With account without move')

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_posted():
        return False

    @staticmethod
    def default_empty_account():
        return False

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
        }


class PrintAuxiliaryBook(Wizard):
    'Print Auxiliary Book'
    __name__ = 'nodux_account_ec.print_auxiliary_book'
    start = StateView('nodux_account_ec.print_auxiliary_book.start',
        'nodux_account_ec.print_auxiliary_book_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('nodux_account_ec.report_auxiliary_book')

    def do_print_(self, action):
        if self.start.start_period:
            start_period = self.start.start_period.id
        else:
            start_period = None
        if self.start.end_period:
            end_period = self.start.end_period.id
        else:
            end_period = None

        if not self.start.party:
            party = None
        else:
            party = self.start.party.id

        start_account_id = None
        if self.start.start_account:
            start_account_id = self.start.start_account.id
        end_account_id = None
        if self.start.end_account:
            end_account_id = self.start.end_account.id


        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'start_period': start_period,
            'end_period': end_period,
            'posted': self.start.posted,
            'start_account': start_account_id,
            'end_account': end_account_id,
            'party': party,
            'empty_account': self.start.empty_account,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class AuxiliaryBook(Report):
    __metaclass__ = PoolMeta
    __name__ = 'account.auxiliary_book'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Account = pool.get('account.account')
        Period = pool.get('account.period')
        Company = pool.get('company.company')
        Party = pool.get('party.party')
        company = Company(data['company'])

        start_period_name = None
        end_period_name = None

        dom_accounts = [
                ('company', '=', data['company']),
                ('kind', '!=', 'view'),
                ]
        start_code = None
        if data['start_account']:
            start_acc = Account(data['start_account'])
            start_code = start_acc.code
            dom_accounts.append(
                ('code', '>=', start_acc.code)
            )
        end_code = None
        if data['end_account']:
            end_acc = Account(data['end_account'])
            end_code = end_acc.code
            dom_accounts.append(
                ('code', '<=', end_acc.code)
            )

        accounts = Account.search(dom_accounts, order=[('code', 'ASC')])

        party = None
        if data['party']:
            party, = Party.search([
                    ('id', '=', data['party']),
                    ])
        # --------------------------------------------------------------
        start_period_ids = [0]
        start_periods = []
        if data['start_period']:
            start_period = Period(data['start_period'])
            start_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ('end_date', '<=', start_period.start_date),
                    ])
            start_period_ids = [p.id for p in start_periods]
            start_period_name = start_period.name

        with Transaction().set_context(
                fiscalyear=data['fiscalyear'],
                periods=start_period_ids,
                party=data['party'],
                posted=data['posted']):
            start_accounts = Account.browse(accounts)
        id2start_account = {}
        for account in start_accounts:
            id2start_account[account.id] = account

        # --------------------------------------------------------------
        end_period_ids = []
        if data['end_period']:
            end_period = Period(data['end_period'])
            end_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ('end_date', '<=', end_period.start_date),
                    ])
            if end_period not in end_periods:
                end_periods.append(end_period)
            end_period_name = end_period.name
        else:
            end_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ])
        end_period_ids = [p.id for p in end_periods]

        with Transaction().set_context(
                fiscalyear=data['fiscalyear'],
                periods=end_period_ids,
                party=data['party'],
                posted=data['posted']):
            end_accounts = Account.browse(accounts)
        id2end_account = {}
        for account in end_accounts:
            id2end_account[account.id] = account

        periods = end_periods
        periods.sort(lambda x, y: cmp(x.start_date, y.start_date))
        periods.sort(lambda x, y: cmp(x.end_date, y.end_date))
        # --------------------------------------------------------------

        if not data['empty_account']:
            account2lines = dict(cls.get_lines(accounts,
                end_periods, data['posted'], data['party']))
            accounts = Account.browse(
                [a.id for a in accounts if a in account2lines]
                )

        account_id2lines = cls.lines(accounts,
            list(set(end_periods).difference(set(start_periods))),
            data['posted'], data['party'])

        # --------------------------------------------------------------
        localcontext['start_period_name'] = start_period_name
        localcontext['end_period_name'] = end_period_name
        localcontext['start_code'] = start_code
        localcontext['end_code'] = end_code
        localcontext['party'] = party
        localcontext['accounts'] = accounts
        localcontext['id2start_account'] = id2start_account
        localcontext['id2end_account'] = id2end_account
        localcontext['digits'] = company.currency.digits
        localcontext['lines'] = lambda account_id: account_id2lines[account_id]
        localcontext['company'] = company
        return super(AuxiliaryBook, cls).parse(report, objects, data,
            localcontext)

    @classmethod
    def get_lines(cls, accounts, periods, posted, party=None):
        MoveLine = Pool().get('account.move.line')
        clause = [
            ('account', 'in', [a.id for a in accounts]),
            ('period', 'in', [p.id for p in periods]),
            ('state', '!=', 'draft'),
            ]
        if party:
            clause.append(('party', '=', party))
        if posted:
            clause.append(('move.state', '=', 'posted'))
        lines = MoveLine.search(clause,
            order=[
                ('account', 'ASC'),
                ('date', 'ASC'),
                ])
        key = operator.attrgetter('account')
        lines.sort(key=key)
        return groupby(lines, key)

    @classmethod
    def lines(cls, accounts, periods, posted, party=None):
        Move = Pool().get('account.move')

        res = dict((a.id, []) for a in accounts)
        account2lines = cls.get_lines(accounts, periods, posted, party)

        state_selections = dict(Move.fields_get(
                fields_names=['state'])['state']['selection'])

        for account, lines in account2lines:
            balance = Decimal('0.0')
            for line in lines:
                balance += line.debit - line.credit
                party = ''
                if line.party:
                    party = line.party.rec_name
                res[account.id].append({
                        'date': line.date,
                        'move': line.move.rec_name,
                        'party': party,
                        'debit': line.debit,
                        'credit': line.credit,
                        'balance': balance,
                        'description': line.move.description or line.description or '',
                        'origin': (line.move.origin.rec_name
                            if line.move.origin else ''),
                        'state': state_selections.get(line.move.state,
                            line.move.state),
                        })
        return res


class PortfolioByPartyDetailed(Report):
    __metaclass__ = PoolMeta
    __name__ = 'party.portfolio_party_detailed'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        AccountInvoice = pool.get('account.invoice')
        new_objects = []
        now = date.today()
        for party in objects:
            invoices = AccountInvoice.search([
                    ('party', '=', party.id),
                    ('state', 'not in', ['paid', 'cancel']),
                    ], order=[('id', 'ASC')])
            new_invoices = []
            sum_invoices = 0
            sum_amount_to_pay = 0
            if not invoices:
                continue

            for invoice in invoices:
                sum_invoices += invoice.total_amount
                sum_amount_to_pay += invoice.amount_to_pay
                if invoice.invoice_date:
                    invoice.aged = (now - invoice.invoice_date).days
                else:
                    invoice.aged = ''
                new_invoices.append(invoice)

            party.invoices = new_invoices
            party.sum_invoices = sum_invoices
            party.sum_amount_to_pay = sum_amount_to_pay
            new_objects.append(party)
        return super(PortfolioByPartyDetailed, cls).parse(report,
                new_objects, data, localcontext)

class PrintTrialBalanceDetailedStart(ModelView):
    'Print Trial Balance Detailed'
    __name__ = 'nodux_account_ec.print_trial_balance_detailed.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True, depends=['start_period', 'end_period'])
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date'))
            ],
        depends=['end_period', 'fiscalyear'])
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        depends=['start_period', 'fiscalyear'])
    party = fields.Many2One('party.party', 'Party')
    company = fields.Many2One('company.company', 'Company', required=True)
    posted = fields.Boolean('Posted Move', help='Show only posted move')
    empty_account = fields.Boolean('Empty Account',
            help='With account without move')

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_posted():
        return False

    @staticmethod
    def default_empty_account():
        return False

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
            }

class PrintTrialBalanceDetailed(Wizard):
    'Print Trial Balance Detailed'
    __name__ = 'nodux_account_ec.print_trial_balance_detailed'
    start = StateView('nodux_account_ec.print_trial_balance_detailed.start',
        'nodux_account_ec.print_trial_balance_detailed_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('nodux_account_ec.report_trial_balance_detailed')

    def do_print_(self, action):
        if self.start.start_period:
            start_period = self.start.start_period.id
        else:
            start_period = None
        if self.start.end_period:
            end_period = self.start.end_period.id
        else:
            end_period = None
        if self.start.party:
            party_id = self.start.party.id
        else:
            party_id = None
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'start_period': start_period,
            'end_period': end_period,
            'party': party_id,
            'posted': self.start.posted,
            'empty_account': self.start.empty_account,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class TrialBalanceDetailed(Report):
    __name__ = 'nodux_account_ec.trial_balance_detailed'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Account = pool.get('account.account')
        Move = pool.get('account.move')
        Line = pool.get('account.move.line')
        Period = pool.get('account.period')
        Company = pool.get('company.company')
        Party = pool.get('party.party')
        FiscalYear = pool.get('account.fiscalyear')
        cursor = Transaction().cursor

        move = Move.__table__()
        line = Line.__table__()
        start_period_name = None
        end_period_name = None

        # ----- Set Periods -----
        start_periods = []
        if data['start_period']:
            start_period = Period(data['start_period'])
            start_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ('end_date', '<=', start_period.start_date),
                    ])
            start_period_name = start_period.name

        if data['end_period']:
            end_period = Period(data['end_period'])
            end_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ('end_date', '<=', end_period.start_date),
                    ])
            end_periods = list(set(end_periods).difference(
                    set(start_periods)))
            end_period_name = end_period.name
            if end_period not in end_periods:
                end_periods.append(end_period)
        else:
            end_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ])
            end_periods = list(set(end_periods).difference(
                    set(start_periods)))

        # Select Query for In
        in_periods = [p.id for p in end_periods]
        move_ = move.select(move.id, where = (move.period.in_(in_periods)))
        select_ = line.select(
                line.account, line.party, Sum(line.debit), Sum(line.credit),
                where=line.move.in_(move_),
                group_by=(line.account, line.party),
                order_by=line.account,
                )
        if data['party']:
            where_party = select_.where & (line.party == data['party'])
            select_.where = select_.where & where_party
        cursor.execute(*select_)
        res = cursor.fetchall()

        id2account = {}
        id2party = {}
        accs_ids = []
        parties_ids = []
        for r in res:
            accs_ids.append(r[0])
            if r[1]:
                parties_ids.append(r[1])
        for acc in Account.browse(accs_ids):
            id2account[acc.id] = acc
        for party in Party.browse(parties_ids):
            id2party[party.id] = party

        # Select Query for Start
        start_periods_ids = [p.id for p in start_periods]
        start_accounts = {}
        if start_periods_ids:
            move_ = move.select(move.id)
            move_.where = (move.period.in_(start_periods_ids))

            select_ = line.select(
                    line.account, line.party, Sum(line.debit) - Sum(line.credit),
                    where=line.move.in_(move_) & line.account.in_(accs_ids),
                    group_by=(line.account, line.party),
                    order_by=line.account,
                    )

            if data['party']:
                select_.where = select_.where & where_party

            cursor.execute(*select_)

            res_start = cursor.fetchall()

            for r in res_start:
                acc_obj = id2account[r[0]]
                code = fmt_acc(acc_obj.code)
                if code not in start_accounts.keys():
                    start_accounts[code] = {}
                start_accounts[code].update({r[1]: r[2]})

        accounts = {}
        for r in res:
            vat_number = ''
            party = ''
            if r[1]:
                party = id2party[r[1]].name
                vat_number = id2party[r[1]].vat_number
            acc_obj = id2account[r[0]]
            code = fmt_acc(acc_obj.code)
            if code not in accounts.keys():
                accounts[code] = [
                    acc_obj, [], {'debits': 0, 'credits': 0}
                    ]
            start_balance = 0
            if start_accounts and start_accounts.get(code) and \
                    start_accounts[code].get(r[1]):
                    start_balance = start_accounts[code][r[1]]
            values = {
                'vat_number': vat_number,
                'party': party,
                'start_balance': start_balance,
                'debit': r[2],
                'credit': r[3],
                'end_balance': start_balance + r[2] - r[3],
            }
            accounts[code][1].append(values)
            accounts[code][2]['debits'] += r[2]
            accounts[code][2]['credits'] += r[3]

        localcontext['accounts'] = OrderedDict(sorted(accounts.items()))
        localcontext['fiscalyear'] = FiscalYear(data['fiscalyear'])
        localcontext['start_period'] = start_period_name
        localcontext['end_period'] = end_period_name
        localcontext['company'] = Company(data['company'])
        return super(TrialBalanceDetailed, cls).parse(report, objects, data,
            localcontext)


class AuxiliaryPartyStart(ModelView):
    'Auxiliary Party Start'
    __name__ = 'nodux_account_ec.print_auxiliary_party.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True)
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ], depends=['fiscalyear', 'end_period'])
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        depends=['fiscalyear', 'start_period'])
    party = fields.Many2One('party.party', 'Party', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)
    posted = fields.Boolean('Posted Move', help='Show only posted move')
    empty_account = fields.Boolean('Empty Account',
            help='With account without move')

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_posted():
        return False

    @staticmethod
    def default_empty_account():
        return False

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
            }


class PrintAuxiliaryParty(Wizard):
    'Print Auxiliary Party'
    __name__ = 'nodux_account_ec.print_auxiliary_party'
    start = StateView('nodux_account_ec.print_auxiliary_party.start',
        'nodux_account_ec.print_auxiliary_party_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('nodux_account_ec.report_auxiliary_party')

    def do_print_(self, action):
        if self.start.start_period:
            start_period = self.start.start_period.id
        else:
            start_period = None
        if self.start.end_period:
            end_period = self.start.end_period.id
        else:
            end_period = None
        if not self.start.party:
            party = None
        else:
            party = self.start.party.id
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'start_period': start_period,
            'end_period': end_period,
            'posted': self.start.posted,
            'party': party,
            'empty_account': self.start.empty_account,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class AuxiliaryParty(Report):
    __name__ = 'account.auxiliary_party'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Period = pool.get('account.period')
        Company = pool.get('company.company')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Party = pool.get('party.party')
        company = Company(data['company'])
        dom_move = []
        #Add context Transaction for company and fiscalyear
        #    dom_move = [('company', '=', company)]
        if data.get('posted'):
            dom_move.append(('state', '=', 'posted'))
        if data.get('start_period'):
            dom_move.append(('period', '>=', data['start_period']))
        if data.get('end_period'):
            dom_move.append(('period', '<=', data['end_period']))

        moves = Move.search_read(dom_move, order=[
                ('date', 'ASC'), ('id', 'ASC')
                ], fields_names=['id'],
        )
        moves_ids = [move['id'] for move in moves]
        objects = []

        lines = MoveLine.search([
                ('move', 'in', moves_ids),
                ('party', '=', data['party']),
                ], order=[('id', 'ASC')])
        start_period = None
        end_period = None
        if lines:
            debits_ = []
            credits_ = []
            new_lines = []

            for line in lines:
                new_line = {
                    'date': line.move.date,
                    'post_number': line.move.post_number,
                    'account_code': line.account.code,
                    'account_name': line.account.name,
                    'description': line.description,
                    'debit': line.debit,
                    'credit': line.credit,
                    'base': None,
                }
                base = Decimal(0)
                for tax_line in line.tax_lines:
                    if tax_line.tax.invoice_tax_code != tax_line.code:
                        continue
                    for l in line.move.lines:
                        for tx_line in l.tax_lines:
                            if tx_line.code == tax_line.tax.invoice_base_code:
                                base += tx_line.amount
                new_line.update({'base': base})
                new_lines.append(new_line)
                debits_.append(line.debit)
                credits_.append(line.credit)
            db = sum(debits_)
            cr = sum(credits_)
            party = Party(data['party'])
            objects.append({
                    'name': party.rec_name,
                    'vat_number': party.vat_number,
                    'lines': new_lines,
                    'debit': db,
                    'credit': cr,
                    'balance': (db - cr),
                    })
            if data['start_period']:
                start_period = Period(data['start_period'])
                start_period = start_period.name
            if data['end_period']:
                end_period = Period(data['end_period'])
                end_period = end_period.name
        localcontext['start_period'] = start_period
        localcontext['end_period'] = end_period
        localcontext['company'] = company
        return super(AuxiliaryParty, cls).parse(report, objects, data,
                localcontext)


class PrintTrialBalanceStart:
    'Print Trial Balance'
    __name__ = 'account.print_trial_balance.start'
    accounts_with_balance = fields.Boolean('Accounts with Balance',
            help='Show accounts with balances in previous periods')


class PrintTrialBalance:
    'Print Trial Balance'
    __name__ = 'account.print_trial_balance'

    def do_print_(self, action):
        action, data = super(PrintTrialBalance, self).do_print_(action)
        data.update({
                'accounts_with_balance': self.start.accounts_with_balance,
                })
        return action, data


class TrialBalance:
    __metaclass__ = PoolMeta
    __name__ = 'account.trial_balance'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Account = pool.get('account.account')
        Period = pool.get('account.period')
        Company = pool.get('company.company')

        company = Company(data['company'])

        accounts = Account.search([
                ('company', '=', data['company']),
                ('kind', '!=', 'view'),
                ])

        start_periods = []
        if data['start_period']:
            start_period = Period(data['start_period'])
            start_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ('end_date', '<=', start_period.start_date),
                    ])

        if data['end_period']:
            end_period = Period(data['end_period'])
            end_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ('end_date', '<=', end_period.start_date),
                    ])
            end_periods = list(set(end_periods).difference(
                    set(start_periods)))
            if end_period not in end_periods:
                end_periods.append(end_period)
        else:
            end_periods = Period.search([
                    ('fiscalyear', '=', data['fiscalyear']),
                    ])
            end_periods = list(set(end_periods).difference(
                    set(start_periods)))

        start_period_ids = [p.id for p in start_periods] or [0]
        end_period_ids = [p.id for p in end_periods]

        with Transaction().set_context(
                fiscalyear=data['fiscalyear'],
                periods=start_period_ids,
                posted=data['posted']):
            start_accounts = Account.browse(accounts)

        with Transaction().set_context(
                fiscalyear=None,
                periods=end_period_ids,
                posted=data['posted']):
            in_accounts = Account.browse(accounts)

        with Transaction().set_context(
                fiscalyear=data['fiscalyear'],
                periods=start_period_ids + end_period_ids,
                posted=data['posted']):
            end_accounts = Account.browse(accounts)
#En account solo to_remove cambia
        to_remove = []
        if not data['empty_account']:
            for account in in_accounts:
                if account.debit == Decimal('0.0') \
                        and account.credit == Decimal('0.0'):
                    to_remove.append(account.id)
#Edita el campo que agrego
        accounts = []
        for start_account, in_account, end_account in izip(
                start_accounts, in_accounts, end_accounts):
            if in_account.id in to_remove:
                if not data['accounts_with_balance'] or \
                    start_account.balance == Decimal('0.0'):
                    continue

            accounts.append({
                    'code': start_account.code,
                    'name': start_account.name,
                    'start_balance': start_account.balance,
                    'debit': in_account.debit,
                    'credit': in_account.credit,
                    'end_balance': end_account.balance,
                    })

        periods = end_periods
        localcontext['accounts'] = accounts
        periods.sort(key=operator.attrgetter('start_date'))
        localcontext['start_period'] = periods[0]
        periods.sort(key=operator.attrgetter('end_date'))
        localcontext['end_period'] = periods[-1]
        localcontext['company'] = company
        localcontext['digits'] = company.currency.digits
        localcontext['sum'] = lambda accounts, field: cls.sum(accounts, field)
        return Report.parse(report, objects, data, localcontext)
    @classmethod
    def sum(cls, accounts, field):
        amount = Decimal('0.0')
        for account in accounts:
            amount += account[field]
        return amount

class BalanceSheet(Report):
    'Sheet Balance'
    __name__ = 'account.balance_sheet'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        User = pool.get('res.user')

        user = User(Transaction().user)

        if user.company.timezone:
            timezone = pytz.timezone(user.company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)

        localcontext['fecha'] = hora.strftime('%d/%m/%Y')
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['company'] = user.company
        localcontext['date'] = Transaction().context.get('date')
        return super(BalanceSheet, cls).parse(report, objects, data, localcontext)

class IncomeStatement(Report):
    'Income Statement'
    __name__ = 'account.income_statement'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        User = pool.get('res.user')
        user = User(Transaction().user)
        if user.company.timezone:
            timezone = pytz.timezone(user.company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)

        localcontext['fecha'] = hora.strftime('%d/%m/%Y')
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['company'] = user.company
        localcontext['date'] = Transaction().context.get('date')
        return super(IncomeStatement, cls).parse(report, objects, data, localcontext)

class CashflowTemplate(ModelSQL, ModelView):
    'Account Cashflow Template'
    __name__ = 'account.account.cashflow.template'
    name = fields.Char('Name', required=True, translate=True)
    parent = fields.Many2One('account.account.cashflow.template', 'Parent',
            ondelete="RESTRICT")
    childs = fields.One2Many('account.account.cashflow.template', 'parent',
        'Children')
    sequence = fields.Integer('Sequence')
    display_balance = fields.Selection([
        ('debit-credit', 'Debit - Credit'),
        ('credit-debit', 'Credit - Debit'),
        ], 'Display Balance', required=True)

    @classmethod
    def __setup__(cls):
        super(CashflowTemplate, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        table = TableHandler(cls, module_name)

        super(CashflowTemplate, cls).__register__(module_name)

        # Migration from 2.4: drop required on sequence
        table.not_null_action('sequence', action='remove')


    @classmethod
    def validate(cls, records):
        super(CashflowTemplate, cls).validate(records)
        cls.check_recursion(records, rec_name='name')

    @staticmethod
    def order_sequence(tables):
        table, _ = tables[None]
        #return [table.sequence == None, table.sequence]
        return [Case((table.sequence == Null, 0), else_=1), table.sequence]

    @staticmethod
    def default_display_balance():
        return 'debit-credit'

    def get_rec_name(self, name):
        if self.parent:
            return self.parent.get_rec_name(name) + '\\' + self.name
        else:
            return self.name

    def _get_cashflow_value(self, cashflow=None):
        '''
        Set the values for account creation.
        '''
        res = {}
        if not cashflow or cashflow.name != self.name:
            res['name'] = self.name
        if not cashflow or cashflow.sequence != self.sequence:
            res['sequence'] = self.sequence
        if not cashflow or cashflow.display_balance != self.display_balance:
            res['display_balance'] = self.display_balance
        if not cashflow or cashflow.template != self:
            res['template'] = self.id
        return res

    def create_cashflow(self, company_id, template2cashflow=None, parent_id=None):
        '''
        Create recursively cashflows based on template.
        template2cashflow is a dictionary with template id as key and cashflow id as
        value, used to convert template id into cashflow. The dictionary is filled
        with new cashflows.
        Return the id of the cashflow created
        '''
        pool = Pool()
        Cashflow = pool.get('account.account.cashflow')
        Lang = pool.get('ir.lang')
        Config = pool.get('ir.configuration')

        if template2cashflow is None:
            template2cashflow = {}

        if self.id not in template2cashflow:
            vals = self._get_cashflow_value()
            vals['company'] = company_id
            vals['parent'] = parent_id

            new_cashflow, = Cashflow.create([vals])

            prev_lang = self._context.get('language') or Config.get_language()
            prev_data = {}
            for field_name, field in self._fields.iteritems():
                if getattr(field, 'translate', False):
                    prev_data[field_name] = getattr(self, field_name)
            for lang in Lang.get_translatable_languages():
                if lang == prev_lang:
                    continue
                with Transaction().set_context(language=lang):
                    template = self.__class__(self.id)
                    data = {}
                    for field_name, field in template._fields.iteritems():
                        if (getattr(field, 'translate', False)
                                and (getattr(template, field_name) !=
                                    prev_data[field_name])):
                            data[field_name] = getattr(template, field_name)
                    if data:
                        Cashflow.write([new_cashflow], data)
            template2cashflow[self.id] = new_cashflow.id
        new_id = template2cashflow[self.id]

        new_childs = []
        for child in self.childs:
            new_childs.append(child.create_cashflow(company_id,
                template2cashflow=template2cashflow, parent_id=new_id))
        return new_id


class Cashflow(ModelSQL, ModelView):
    'Account Cashflow'
    __name__ = 'account.account.cashflow'
    name = fields.Char('Name', size=None, required=True, translate=True)
    parent = fields.Many2One('account.account.cashflow', 'Parent',
        ondelete="RESTRICT", domain=[
            ('company', '=', Eval('company')),
            ], depends=['company'])
    childs = fields.One2Many('account.account.cashflow', 'parent', 'Children',
        domain=[
            ('company', '=', Eval('company')),
        ], depends=['company'])
    sequence = fields.Integer('Sequence',
        help='Use to order the account cashflow')
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
            'get_currency_digits')
    amount = fields.Function(fields.Numeric('Amount',
        digits=(16, Eval('currency_digits', 2)), depends=['currency_digits']),
        'get_amount')
    display_balance = fields.Selection([
        ('debit-credit', 'Debit - Credit'),
        ('credit-debit', 'Credit - Debit'),
        ], 'Display Balance', required=True)
    company = fields.Many2One('company.company', 'Company', required=True,
            ondelete="RESTRICT")
    template = fields.Many2One('account.account.cashflow.template', 'Template')
    accounts = fields.One2Many('account.account', 'cashflow', 'Accounts',
            add_remove=[], domain=[
                ('kind', '!=', 'view'),
            ])

    @classmethod
    def __setup__(cls):
        super(Cashflow, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        table = TableHandler(cls, module_name)

        super(Cashflow, cls).__register__(module_name)

        # Migration from 2.4: drop required on sequence
        table.not_null_action('sequence', action='remove')

    @classmethod
    def validate(cls, cashflows):
        super(Cashflow, cls).validate(cashflows)
        cls.check_recursion(cashflows, rec_name='name')

    @staticmethod
    def order_sequence(tables):
        table, _ = tables[None]
        return [Case((table.sequence == Null, 0), else_=1), table.sequence]

    @staticmethod
    def default_balance_sheet():
        return False

    @staticmethod
    def default_income_statement():
        return False

    @staticmethod
    def default_display_balance():
        return 'debit-credit'

    def get_currency_digits(self, name):
        return self.company.currency.digits

    @classmethod
    def get_amount(cls, cashflows, name):
        pool = Pool()
        Account = pool.get('account.account')

        res = {}
        for cashflow_ in cashflows:
            res[cashflow_.id] = Decimal('0.0')

        childs = cls.search([
                ('parent', 'child_of', [t.id for t in cashflows]),
                ])
        cashflow_sum = {}
        for cashflow_ in childs:
            cashflow_sum[cashflow_.id] = Decimal('0.0')

        accounts = Account.search([
                ('cashflow', 'in', [t.id for t in childs]),
                ('kind', '!=', 'view'),
                ])
        for account in accounts:
            cashflow_sum[account.cashflow.id] += (account.debit - account.credit)

        for cashflow_ in cashflows:
            childs = cls.search([
                    ('parent', 'child_of', [cashflow_.id]),
                    ])
            for child in childs:
                res[cashflow_.id] += cashflow_sum[child.id]
            res[cashflow_.id] = cashflow_.company.currency.round(res[cashflow_.id])
            if cashflow_.display_balance == 'credit-debit':
                res[cashflow_.id] = - res[cashflow_.id]
        return res

    def get_rec_name(self, name):
        if self.parent:
            return self.parent.get_rec_name(name) + '\\' + self.name
        else:
            return self.name

    @classmethod
    def delete(cls, cashflows):
        cashflows = cls.search([
                ('parent', 'child_of', [t.id for t in cashflows]),
                ])
        super(Cashflow, cls).delete(cashflows)

    def update_cashflow(self, template2cashflow=None):
        '''
        Update recursively cashflows based on template.
        template2cashflow is a dictionary with template id as key and cashflow id as
        value, used to convert template id into cashflow. The dictionary is filled
        with new cashflows
        '''
        pool = Pool()
        Lang = pool.get('ir.lang')
        Config = pool.get('ir.configuration')

        if template2cashflow is None:
            template2cashflow = {}

        if self.template:
            vals = self.template._get_cashflow_value(cashflow=self)
            if vals:
                self.write([self], vals)

            prev_lang = self._context.get('language') or Config.get_language()
            prev_data = {}
            for field_name, field in self.template._fields.iteritems():
                if getattr(field, 'translate', False):
                    prev_data[field_name] = getattr(self.template, field_name)
            for lang in Lang.get_translatable_languages():
                if lang == prev_lang:
                    continue
                with Transaction().set_context(language=lang):
                    cashflow_ = self.__class__(self.id)
                    data = {}
                    for field_name, field in (
                            cashflow_.template._fields.iteritems()):
                        if (getattr(field, 'translate', False)
                                and (getattr(cashflow_.template, field_name) !=
                                    prev_data[field_name])):
                            data[field_name] = getattr(cashflow_.template,
                                field_name)
                    if data:
                        self.write([cashflow_], data)
            template2cashflow[self.template.id] = self.id

        for child in self.childs:
            child.update_cashflow(template2cashflow=template2cashflow)

class OpenCashflowStart(ModelView):
    'Open Cashflow Statement'
    __name__ = 'account.open_cashflow_statement.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True)
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date'))
            ],
        depends=['end_period', 'fiscalyear'])
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date')),
            ],
        depends=['start_period', 'fiscalyear'])
    company = fields.Many2One('company.company', 'Company', required=True)
    posted = fields.Boolean('Posted Move', help='Show only posted move')

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_posted():
        return False

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
            }


class OpenCashflowStatement(Wizard):
    'Open Cashflow Statement'
    __name__ = 'account.open_cashflow_statement'
    start = StateView('account.open_cashflow_statement.start',
        'nodux_account_ec.open_cashflow_statement_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'open_', 'tryton-ok', default=True),
            ])
    open_ = StateAction('nodux_account_ec.act_account_cashflow_statement_tree')

    def do_open_(self, action):
        pool = Pool()
        Period = pool.get('account.period')

        start_periods = []
        if self.start.start_period:
            start_periods = Period.search([
                    ('fiscalyear', '=', self.start.fiscalyear.id),
                    ('end_date', '<=', self.start.start_period.start_date),
                    ])

        end_periods = []
        if self.start.end_period:
            end_periods = Period.search([
                    ('fiscalyear', '=', self.start.fiscalyear.id),
                    ('end_date', '<=', self.start.end_period.start_date),
                    ])
            end_periods = list(set(end_periods).difference(
                    set(start_periods)))
            if self.start.end_period not in end_periods:
                end_periods.append(self.start.end_period)
        else:
            end_periods = Period.search([
                    ('fiscalyear', '=', self.start.fiscalyear.id),
                    ])
            end_periods = list(set(end_periods).difference(
                    set(start_periods)))

        action['pyson_context'] = PYSONEncoder().encode({
                'periods': [p.id for p in end_periods],
                'posted': self.start.posted,
                'company': self.start.company.id,
                })
        return action, {}


class CashFlowStatement(Report):
    'CashFlow Statement'
    __name__ = 'account.cashflow_statement'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        localcontext['company'] = Transaction().context.get('company.rec_name')
        localcontext['date'] = Transaction().context.get('date')
        return super(CashFlowStatement, cls).parse(report, objects, data, localcontext)

class PartyWithholdingStart(ModelView):
    'Party Withholding Start'
    __name__ = 'account.party_withholding.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscalyear',
        required=True)
    company = fields.Many2One('company.company', 'Company', required=True)
    party = fields.Many2One('party.party', 'Party')
    certificate_report = fields.Selection('selection_certificate_report',
        'Certificate Report', required=True)
    start_period = fields.Many2One('account.period', 'Start Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ], depends=['fiscalyear', 'end_period'])
    end_period = fields.Many2One('account.period', 'End Period',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        depends=['fiscalyear', 'start_period'])

    @staticmethod
    def default_company():
        return Transaction().context.get('company')


    @classmethod
    def selection_certificate_report(cls):
        Tax = Pool().get('account.tax')
        sel = Tax.certificate_report.selection
        return sel


class PrintPartyWithholding(Wizard):
    'Print Withholding'
    __name__ = 'account.print_party_withholding'
    start = StateView('account.party_withholding.start',
        'nodux_account_ec.print_party_withholding_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'print_', 'tryton-ok', default=True),
            ])
    print_ = StateAction('nodux_account_ec.report_party_withholding')

    def do_print_(self, action):
        if self.start.start_period:
            start_period = self.start.start_period.id
        else:
            start_period = None
        if self.start.end_period:
            end_period = self.start.end_period.id
        else:
            end_period = None

        party_id = None
        if self.start.party:
            party_id = self.start.party.id
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'party': party_id,
            'certificate_report': self.start.certificate_report,
            'start_period': start_period,
            'end_period': end_period,
            }
        return action, data


class PartyWithholding(CompanyReport):
    __name__ = 'account.party_withholding'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        InvoiceTax = pool.get('account.invoice.tax')
        Tax = pool.get('account.tax')
        Company = pool.get('company.company')
        Period = pool.get('account.period')
        Fiscalyear = pool.get('account.fiscalyear')
        Party = pool.get('party.party')

        company = Company(data['company'])
        parties_ids = []
        if data['party']:
            parties_ids.append(data['party'])
            party_dom = [
                ('id', 'in', parties_ids),
            ]
        else:
            party_dom = []
        parties = Party.search(party_dom)

        periods = Period.search_read([
                ('fiscalyear', '=', data['fiscalyear']),
            ], fields_names=['id'])
        period_ids = [p.values()[0] for p in periods]

        taxes = Tax.search_read([
            ('certificate_report', '=', data['certificate_report'])
            ], fields_names=['id'])
        tax_ids = [t.values()[0] for t in taxes]

        objects = []
        for party in parties:
            invoice_taxes = InvoiceTax.search([
                    ('invoice.move.period', 'in', period_ids),
                    ('invoice.party', '=', party.id),
                    ('invoice.state', '=', 'posted'),
                    ('tax', 'in', tax_ids),
                    ], order=[('create_date', 'ASC')])
            if not invoice_taxes:
                continue
            total_amount = sum([abs(i.amount) for i in invoice_taxes])
            setattr(party, 'taxes', invoice_taxes)
            setattr(party, 'total_amount', total_amount)
            objects.append(party)

        localcontext['fiscalyear'] = Fiscalyear(data['fiscalyear'])
        localcontext['today'] = date.today()
        localcontext['company'] = company
        localcontext['reporte'] = data['certificate_report']
        return super(PartyWithholding, cls).parse(report, objects, data,
                localcontext)

class OpenAgedBalanceStart:
    __name__ = 'account.open_aged_balance.start'
    employee = fields.Many2One('res.user','Employee', states={
            'invisible': Eval('balance_type')!= 'customer',
            }, depends=['balance_type'])

    @classmethod
    def __setup__(cls):
        super(OpenAgedBalanceStart, cls).__setup__()

class OpenAgedBalance:
    __name__='account._open_aged_balance'

    def do_print_(self, action):
        data = {
            'employee': self.start.employee.id,
            'category': self.start.category.id,
            }
        return action, data

class AgedBalance:
    __name__ = 'account.aged_balance'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        return super(AgedBalance, cls).parse(report, objects, data,
            localcontext)

class OpenCostAnalitic(ModelView):
    'Open Cost Analitic'
    __name__ = 'nodux_account_ec.print_cost_analitic.start'
    fecha = fields.Date('Fecha de ventas', help='Fecha para analitico de costo de ventas')
    company = fields.Many2One('company.company', 'Company', required=True)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')


    @staticmethod
    def default_fecha():
        Date = Pool().get('ir.date')
        date = Date.today()
        return date

class OpenAnalitic(Wizard):
    'Open Analitic'
    __name__ = 'nodux_account_ec.print_cost_analitic'

    start = StateView('nodux_account_ec.print_cost_analitic.start',
        'nodux_account_ec.print_cost_analitic_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-ok', default=True),
            ])
    print_ = StateAction('nodux_account_ec.report_cost_analitic')

    def do_print_(self, action):
        if self.start.fecha:
            fecha = self.start.fecha
        if self.start.company:
            company = self.start.company

        data = {
            'fecha': fecha,
            'company': company.id,
            }
        return action, data

    def transition_print_(self):
        return 'end'

class TotalAnaliticCost(Report):
    'Total Analitic Cost'
    __name__ = 'nodux_account_ec.cost_analitic'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Company = pool.get('company.company')
        Sale = pool.get('sale.sale')
        SaleLine = pool.get('sale.line')
        fecha = data['fecha']
        company = Company(data['company'])

        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            Date = Pool().get('ir.date')
            date = datetime.today()
            dt = date
            print "La fecha ", dt
            fecha_im = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)

        sales = Sale.search([('sale_date', '=', fecha)])
        s_lines = []
        print "Asientos ", sales

        for s in sales:
            sale_lines = SaleLine.search([('sale','=', s.id)])
            for s_l in sale_lines:
                s_lines.append(s_l)

        print "Lineas ", s_lines
        for s in s_lines:
            print "La venta ",s.product.customer_taxes
        localcontext['fecha'] = fecha
        localcontext['lines'] = s_lines
        localcontext['company'] = company
        localcontext['fecha_im'] =  fecha_im

        return super(TotalAnaliticCost, cls).parse(report, objects, data,
            localcontext)

class OpenTotalSale(ModelView):
    'Open Total Sale'
    __name__ = 'nodux_account_ec.print_total_sale.start'
    fecha = fields.Date('Fecha de ventas', help='Fecha para asiento de ventas')
    company = fields.Many2One('company.company', 'Company', required=True)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_fecha():
        Date = Pool().get('ir.date')
        date = Date.today()
        return date

class TotalSale(Wizard):
    'Total Sale'
    __name__ = 'nodux_account_ec.print_total_sale'

    start = StateView('nodux_account_ec.print_total_sale.start',
        'nodux_account_ec.print_total_sale_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-ok', default=True),
            ])
    print_ = StateAction('nodux_account_ec.report_total_sale')

    def do_print_(self, action):
        if self.start.fecha:
            fecha = self.start.fecha
        if self.start.company:
            company = self.start.company

        data = {
            'fecha': fecha,
            'company': company.id,
            }
        return action, data

    def transition_print_(self):
        return 'end'

class TotalSaleReport(Report):
    'Total Sale Report'
    __name__ = 'nodux_account_ec.total_sale'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Company = pool.get('company.company')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        fecha = data['fecha']
        company = Company(data['company'])
        Invoice = pool.get('account.invoice')
        InvoiceLine = pool.get('account.invoice.line')
        Sale = pool.get('sale.sale')
        Account = pool.get('account.account')

        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            Date = Pool().get('ir.date')
            date = datetime.today()
            dt = date
            fecha_im = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)

        print "Lo que tiene el mes ", fecha_im.strftime('%m')
        if (fecha_im.strftime('%m')) == '01':
            mes= 'Enero'
        elif (fecha_im.strftime('%m')) == '02':
            mes= 'Febrero'
        elif (fecha_im.strftime('%m')) == '03':
            mes= 'Marzo'
        elif (fecha_im.strftime('%m')) == '04':
            mes= 'Abril'
        elif (fecha_im.strftime('%m')) == '05':
            mes= 'Mayo'
        elif (fecha_im.strftime('%m')) == '06':
            mes= 'Junio'
        elif (fecha_im.strftime('%m')) == '07':
            mes= 'Julio'
        elif (fecha_im.strftime('%m')) == '08':
            mes= 'Agosto'
        elif (fecha_im.strftime('%m')) == '09':
            mes= 'Septiembre'
        elif (fecha_im.strftime('%m')) == '10':
            mes= 'Octubre'
        elif (fecha_im.strftime('%m')) == '11':
            mes= 'Noviembre'
        elif (fecha_im.strftime('%m')) == '12':
            mes= 'Diciembre'

        invoices = Invoice.search([('invoice_date', '=', fecha)])
        i_lines = []
        t_lines = []
        _0_lines = []
        _12_lines = []
        cuenta = ''
        codigo = ''
        total_debit = Decimal(0.0)
        total_credit = Decimal(0.0)
        total_amount_12 = Decimal(0.0)
        total_amount_0 = Decimal(0.0)
        total_taxes = Decimal(0.0)
        impuesto = Decimal(0.0)
        account_12 = Account.search([('name', '=', 'VENTA DE BIENES')])
        account_0 = Account.search([('name', '=', 'VENTA DE BIENES')])
        account_taxes = Account.search([('name', '=', 'IVA VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA 12%')])

        for i in invoices:
            amount = Decimal(0.0)
            invoices_lines = InvoiceLine.search([('invoice','=', i.id)])
            if i.state == 'paid':
                moves = Move.search([('id', '=', i.move.id)])
                for m in moves:
                    move_lines = MoveLine.search([('description', '=', i.description), ('reconciliation', '=', None)])
                    for mv_lr in move_lines:
                        cuenta = mv_lr.account.name
                        codigo = mv_lr.account.code
                    move_lines_taxes = MoveLine.search([('party', '=', i.party.id), ('reconciliation', '=', None)])
                    for mv_lr_t in move_lines_taxes:
                        #cuenta_impuesto = mv_lr_t.account.name
                        #codigo_impuesto = mv_lr_t.account.code
                        impuesto = impuesto + mv_lr_t.credit

            if i.state != 'paid':
                moves = Move.search([('id', '=', i.move.id)])
                for m in moves:
                    move_lines = MoveLine.search([('description', '=', i.description)])
                    for mv_lr in move_lines:
                        cuenta = mv_lr.account.name
                        codigo = mv_lr.account.code
                    move_lines_taxes = MoveLine.search([('party', '=', i.party.id), ('reconciliation', '=', None)])
                    for mv_lr_t in move_lines_taxes:
                        #cuenta_impuesto = mv_lr_t.account.name
                        #codigo_impuesto = mv_lr_t.account.code
                        impuesto = impuesto + mv_lr_t.credit

            sale = Sale.search([('reference', '=', i.description)])
            for s in sale:
                total = s.total_amount
                amount = s.untaxed_amount
                if s.tax_amount_cache > Decimal(0.0):
                    total_amount_12 = total_amount_12 + amount
                else:
                    total_amount_0 = total_amount_0 + amount
                total_taxes = total_taxes + s.tax_amount_cache
                total_debit = total_debit + total

            i_lines.append({
                'codigo': codigo,
                'cuenta': cuenta,
                'tipo': 'Fac',
                'numero_doc': i.number,
                'debito': total,
                'cliente': i.party,
            })

        for c_12 in account_12:
            codigo_12 = c_12.code
            cuenta_12 = c_12.name

        for c_0 in account_0:
            codigo_0 = c_0.code
            cuenta_0 = c_0.name

        for c_t in account_taxes:
            codigo_impuesto = c_t.code
            cuenta_impuesto = c_t.name

        t_lines.append({
            'codigo': codigo_impuesto,
            'cuenta': cuenta_impuesto,
            'tipo': 'Fac',
            'credito': total_taxes,
        })
        _12_lines.append({
            'codigo': codigo_12,
            'cuenta': cuenta_12,
            'tipo': 'Fac',
            'credito': total_amount_12,
        })
        _0_lines.append({
            'codigo': codigo_0,
            'cuenta': cuenta_0,
            'tipo': 'Fac',
            'credito': total_amount_0,
        })

        total_credit = total_taxes + total_amount_0 + total_amount_12

        localcontext['total_debit'] = total_debit
        localcontext['total_credit'] = total_credit
        localcontext['fecha'] = fecha
        localcontext['mes'] = mes
        localcontext['lines'] = i_lines
        localcontext['company'] = company
        localcontext['fecha_im'] =  fecha_im
        localcontext['lines_t'] = t_lines
        localcontext['lines_12'] = _12_lines
        localcontext['lines_0'] = _0_lines

        return super(TotalSaleReport, cls).parse(report, objects, data,
            localcontext)
