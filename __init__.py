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
        Company,
        Address,
        Configuration,
        CashflowTemplate,
        Cashflow,
        Account,
        Party,
        AuxiliaryBookStart,
        AuxiliaryPartyStart,
        PrintTrialBalanceDetailedStart,
        PrintTrialBalanceStart,
        BankAccountNumber,
        OpenCashflowStart,
        PartyWithholdingStart,
        #TaxesByPeriodStart,
        OpenAgedBalanceStart,
        ATSStart,
        Template,
        Invoice,
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
        ATS,
        CashFlowStatement,
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
        PrintATS,
        module='nodux_account_ec', type_='wizard')
