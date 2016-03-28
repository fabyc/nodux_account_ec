#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.report import Report
from decimal import Decimal

__all__ = ['Invoice', 'InvoiceReport']
        
__metaclass__ = PoolMeta


class Invoice:
    'Invoice'
    __name__ = 'account.invoice'  
    #campos necesarios para guia de remision y comprobante de retencion
    ambiente = fields.Date(u'Fecha de Factura que se modifica')
    number_w = fields.Char('Numero', size=20, readonly=True, select=True)
    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        
class InvoiceReport(Report):
    __name__ = 'account.invoice'
    
    @classmethod
    def parse(cls, report, records, data, localcontext):
        pool = Pool()
        User = pool.get('res.user')
        Invoice = pool.get('account.invoice')

        invoice = records[0]
        
        localcontext['descuento'] = cls._get_descuento(Invoice, invoice)

        return super(InvoiceReport, cls).parse(report, records, data,
                localcontext=localcontext)              
        
    @classmethod
    def _get_descuento(cls, Invoice, invoice):
        descuento = Decimal(0.00)
        descuento_parcial = Decimal(0.00)
                
        for line in invoice.lines:
            descuento_parcial = Decimal(line.product.template.list_price - line.unit_price)
            descuento = descuento + descuento_parcial
            
        return descuento
                 
