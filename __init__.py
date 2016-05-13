#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from .party import *
from .account import *
#from .tax import *
from .product import *
from .invoice import *
def register():
    Pool.register(
        #Tax,
        Party,
        Company,
        BankAccountNumber,
        CashflowTemplate,
        Cashflow,
        Account,
        AuxiliaryBookStart,
        AuxiliaryPartyStart,
        PrintTrialBalanceDetailedStart,
        PrintTrialBalanceStart,
        OpenCashflowStart,
        PartyWithholdingStart,
        #TaxesByPeriodStart,
        OpenAgedBalanceStart,
        Template,
        Invoice,
        #Product,
        module='nodux_account_ec', type_='model')
    Pool.register(
        AuxiliaryBook,
        AuxiliaryParty,
        TrialBalanceDetailed,
        PortfolioByPartyDetailed,
        TrialBalance,
        BalanceSheet,
        IncomeStatement,
        PartyWithholding,
        #TaxesByPeriod,
        AgedBalance,
        CashFlowStatement,
        InvoiceReport,
        module='nodux_account_ec', type_='report')
    Pool.register(
        PrintAuxiliaryBook,
        PrintTrialBalanceDetailed,
        PrintAuxiliaryParty,
        PrintTrialBalance,
        OpenCashflowStatement,
        PrintPartyWithholding,
        #PrintTaxesByPeriod,
        OpenAgedBalance,
        module='nodux_account_ec', type_='wizard')
