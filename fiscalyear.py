# -*- coding: utf-8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, StateAction, \
    Button
from trytond.tools import datetime_strftime
from trytond.pyson import Eval, If, PYSONEncoder
from trytond.pool import Pool, PoolMeta

__all__ = ['FiscalYear']
__metaclass__ = PoolMeta


class FiscalYear():
    'Fiscal Year'
    __name__ = 'account.fiscalyear'

    @classmethod
    def __setup__(cls):
        super(FiscalYear, cls).__setup__()

    @classmethod
    def validate(cls, years):
        super(FiscalYear, cls).validate(years)
        for year in years:
            year.check_dates()
            year.check_post_move_sequence()

    def pre_validate(self):
        self.raise_user_warning('check_sequence', u'Asegúrese que las secuencias sean la continuación del Año Fiscal anterior')
