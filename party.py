#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.pool import *
from trytond.model import fields
from trytond.pyson import Eval
from trytond.pyson import Id

__all__ = ['Party', 'BankAccountNumber', 'Address', 'Company' , 'Configuration']
__metaclass__ = PoolMeta

STATES = {
    'readonly': ~Eval('active', True),
    'required': True,
}
DEPENDS = ['active']

class Party:
    __name__ = 'party.party'
    
    type_document = fields.Selection([
                ('', ''),
                ('04', 'RUC'),
                ('05', 'Cedula'),
                ('06', 'Pasaporte'),
                ('07', 'Consumidor Final'),
            ], 'Type Document', states={
                'readonly': ~Eval('active', True),
            },  depends=['active'])
             
    type_party = fields.Selection([
        ('', ''),
        ('persona_natural', 'Persona Natural'),
        ('entidad_publica', 'Entidad Publica'),
        ('persona_juridica', 'Persona Juridica'),
        ], 'Type Party', states={
                'readonly': ~Eval('active', True),
                'invisible': Eval('type_document') != '04',
                }
        )        
    
    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()
        cls._error_messages.update({
                'invalid_vat_number': ('Invalid VAT Number "%s".')})
        cls._sql_constraints += [
            ('vat_number', 'UNIQUE(vat_number)',
                'VAT Number already exists!'),
        ]

    @staticmethod
    def default_type_document():
        return '05'

    @classmethod
    def search_rec_name(cls, name, clause):
        parties = cls.search([
                ('vat_number',) + tuple(clause[1:]),
                ], limit=1)
        if parties:
            return [('vat_number',) + tuple(clause[1:])]
        return [('name',) + tuple(clause[1:])]

    @classmethod
    def validate(cls, parties):
        for party in parties:
            if party.type_document == '04' and bool(party.vat_number):
                super(Party, cls).validate(parties)

    def pre_validate(self):
        if self.type_document == '':
            pass
        elif self.type_document == '06':
            pass
        else:
            if not self.vat_number:
                return
            if self.vat_number == '9999999999999':
                return
            vat_number = self.vat_number.replace(".", "")
            if vat_number.isdigit() and len(vat_number) > 9:
                is_valid = self.compute_check_digit(vat_number)
                if is_valid:
                    return
            self.raise_user_error('invalid_vat_number', (self.vat_number,))

    def compute_check_digit(self, raw_number):
        "Compute the check digit - Modulus 10 and 11"
        factor = 2
        x = 0
        set_check_digit = None
        if self.type_document == '04':
            # Si es RUC valide segun el tipo de tercero
            if self.type_party == 'persona_natural':
                if len(raw_number) != 13 or int(raw_number[2]) > 5 or raw_number[-3:] != '001':
                    return
                number = raw_number[:9]
                set_check_digit = raw_number[9]
                for n in number:
                    y = int(n) * factor
                    if y >= 10:
                        y = int(str(y)[0]) + int(str(y)[1])
                    x += y
                    if factor == 2:
                        factor = 1
                    else:
                        factor = 2
                res = (x % 10)
                if res ==  0:
                    value = 0
                else:
                    value = 10 - (x % 10)
                return (set_check_digit == str(value))
                    
            elif self.type_party == 'entidad_publica':
                if not len(raw_number) == 13 or raw_number[2] != '6' \
                    or raw_number[-3:] != '001':
                    return
                number = raw_number[:8]
                set_check_digit = raw_number[8]
                for n in reversed(number):
                    x += int(n) * factor
                    factor += 1
                    if factor == 8:
                        factor = 2
                value = 11 - (x % 11)
                if value == 11:
                    value = 0
                return (set_check_digit == str(value))
                    
            else:
                if len(raw_number) != 13 or \
                    (self.type_party in ['persona_juridica'] \
                    and int(raw_number[2]) != 9) or raw_number[-3:] != '001':
                    return
                number = raw_number[:9]
                set_check_digit = raw_number[9]
                for n in reversed(number):
                    x += int(n) * factor
                    factor += 1
                    if factor == 8:
                        factor = 2
                value = 11 - (x % 11)
                if value == 11:
                    value = 0
                return (set_check_digit == str(value))
        else:
            #Si no tiene RUC valide: cedula, pasaporte, consumidor final (cedula)
            if len(raw_number) != 10:
                return
            number = raw_number[:9]
            set_check_digit = raw_number[9]
            for n in number:
                y = int(n) * factor
                if y >= 10:
                    y = int(str(y)[0]) + int(str(y)[1])
                x += y
                if factor == 2:
                    factor = 1
                else:
                    factor = 2
            res = (x % 10)
            if res ==  0:
                value = 0
            else:
                value = 10 - (x % 10)
            return (set_check_digit == str(value))
                        
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


class Address:
    __name__ = 'party.address'

    @staticmethod
    def default_country():
        return Id('country', 'ec').pyson()

class Configuration:
    __name__ = 'party.configuration'
 
    @classmethod
    def default_party_lang(cls):
        Lang = Pool().get('ir.lang')
        langs = Lang.search([('code','=','es_EC')])   
        return langs[0].id

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
