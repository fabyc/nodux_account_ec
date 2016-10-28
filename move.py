#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from decimal import Decimal
import datetime
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pyson import Eval, Bool, PYSONEncoder
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

__all__ = ['Move', 'Line']
__metaclass__ = PoolMeta


class Move(ModelSQL, ModelView):
    'Account Move'
    __name__ = 'account.move'

    @classmethod
    def __setup__(cls):
        super(Move, cls).__setup__()
        del cls.lines.states['readonly']

    @classmethod
    def check_modify(cls, moves):
        'Check posted moves for modifications.'
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        User = pool.get('res.user')
        Group = pool.get('res.group')
        for move in moves:
            def in_group():
                origin = str(move)
                group = Group(ModelData.get_id('nodux_account_ec',
                        'group_move_force'))
                transaction = Transaction()
                user_id = transaction.user
                if user_id == 0:
                    user_id = transaction.context.get('user', user_id)
                if user_id == 0:
                    return True
                user = User(user_id)
                return origin and group in user.groups

            if move.state == 'posted':
                if not in_group():
                    cls.raise_user_error('modify_posted_move', (move.rec_name,))

class Line(ModelSQL, ModelView):
    'Account Move Line'
    __name__ = 'account.move.line'

    @classmethod
    def __setup__(cls):
        super(Line, cls).__setup__()

    @classmethod
    def check_modify(cls, lines, modified_fields=None):
        '''
        Check if the lines can be modified
        '''
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        User = pool.get('res.user')
        Group = pool.get('res.group')
        if (modified_fields is not None
                and modified_fields <= cls._check_modify_exclude):
            return
        journal_period_done = []
        for line in lines:
            def in_group():
                origin = str(line)
                group = Group(ModelData.get_id('nodux_account_ec',
                        'group_move_force'))
                transaction = Transaction()
                user_id = transaction.user
                if user_id == 0:
                    user_id = transaction.context.get('user', user_id)
                if user_id == 0:
                    return True
                user = User(user_id)
                return origin and group in user.groups

            if line.move.state == 'posted':
                if not in_group():
                    cls.raise_user_error('modify_posted_move', (
                            line.move.rec_name,))
            journal_period = (line.journal.id, line.period.id)
            if journal_period not in journal_period_done:
                cls.check_journal_period_modify(line.period,
                        line.journal)
                journal_period_done.append(journal_period)
