#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.pool import *
from trytond.model import fields
from trytond.pyson import Eval
from trytond.pyson import Id
from trytond.pyson import Bool, Eval

__all__ = ['Party', 'BankAccountNumber', 'Company']
__metaclass__ = PoolMeta

STATES = {
    'readonly': ~Eval('active', True),
    'required': True,
}
DEPENDS = ['active']

class Party:
    __name__ = 'party.party'
    
    mandatory_accounting = fields.Selection([
            ('',''),
            ('SI', 'Si'),
            ('NO', 'No'),
            ], 'Mandatory Accounting', states={
                'invisible': Eval('type_document')!='04',
            }
            )  
    contribuyente_especial = fields.Boolean(u'Contribuyente especial', states={
            'invisible': Eval('mandatory_accounting') != 'SI',
            }, help="Seleccione solo si es contribuyente especial"
        )        
    contribuyente_especial_nro = fields.Char('Nro. Resolucion', states={
            'invisible': ~Eval('contribuyente_especial',True),
            'required': Eval('contribuyente_especial',True),
            }, help="Contribuyente Especial Nro.")
    
    type_document = fields.Selection([
                ('', ''),
                ('04', 'RUC'),
                ('05', 'Cedula'),
                ('06', 'Pasaporte'),
                ('07', 'Consumidor Final'),
            ], 'Type Document', states={
                'readonly': ~Eval('active', True),
            },  depends=['active'])
    
class BankAccountNumber:
    __name__ = 'bank.account.number'

    @classmethod
    def __setup__(cls):
        super(BankAccountNumber, cls).__setup__()
        new_sel = [
            ('checking_account', 'Checking Account'),
            ('saving_account', 'Saving Account'),
        ]
        if new_sel not in cls.type.selection:
            cls.type.selection.extend(new_sel)

class Company:
    __name__ = 'company.company'
        
    @classmethod
    def default_currency(cls):
        Currency = Pool().get('currency.currency')
        usd= Currency.search([('code','=','USD')])        
        return usd[0].id
            
    @staticmethod
    def default_timezone():
        return 'America/Guayaquil'
