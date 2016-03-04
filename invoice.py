#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool

__all__ = ['Invoice']
        
__metaclass__ = PoolMeta


class Invoice:
    'Invoice'
    __name__ = 'account.invoice'  
    #campos necesarios para guia de remision y comprobante de retencion
    ambiente = fields.Date(u'Fecha de Factura que se modifica')
    number_w = fields.Char('Number', size=20, readonly=True, select=True)
    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
       
