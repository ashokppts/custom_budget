# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#
#    Copyright (c) 2011 Vauxoo - http://www.vauxoo.com/
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
############################################################################
#    Coded by: Nhomar <nhomar@vauxoo.com>
############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import time
import datetime
from datetime import timedelta
import locale

def strToDate(dt):
        dt_date=datetime.date(int(dt[0:4]),int(dt[5:7]),int(dt[8:10]))
        return dt_date

class crossovered_budget(osv.osv):
    _inherit = "crossovered.budget"
    _description = "Budget"

    _columns = {
        'dt_approved': fields.date('Date Approved',
                                   readonly=True),
        'dt_validated': fields.date('Date Validated',
                                    readonly=True),
        'dt_done': fields.date('Date Done',
                               readonly=True,
                               help="Date when the cicle finish."),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year',
                                     help="Period for this budget"),
        'period_id': fields.many2one('account.period', 'Period',
                                     help="Period for this budget"),
        'date_from': fields.date('Start Date', states={'done': [('readonly', True)]}),
        'date_to': fields.date('End Date', states={'done': [('readonly', True)]}),
        'company_id': fields.many2one('res.company', 'Company'),
        'general_budget_id': fields.many2one('account.budget.post', 'Budgetary Position'),
    }

    _default = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }


class crossovered_budget_lines(osv.osv):
    _inherit = 'crossovered.budget.lines'

    def _prac_acc(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = self._prac_amt_acc(cr, uid, [line.id], context=context)[line.id]
        return res
    
    def _planned_amount_int(self, cr, uid, ids, name, args, context=None):
        res = {}
        locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        tempString = ''
        for line in self.browse(cr, uid, ids, context=context):
            temp = line.planned_amount
            if temp:
                tempString = locale.format("%d", temp, grouping=True)
                res[line.id] = tempString
            else:
                tempString = "0"
        return res

    def _get_ifrs_total(self, cr, uid, ids, name, args, context=None):
        res = {}
        cbl_brws = self.browse(cr, uid, ids, context=context)
        ifrs_line_obj = self.pool.get('ifrs.lines')
        ifrs_ifrs_obj = self.pool.get('ifrs.ifrs')
        dt = None
        for line in cbl_brws:
            dt = datetime.datetime.strptime(line.period_id.date_stop, '%Y-%m-%d')
            period_name = ifrs_ifrs_obj._get_periods_name_list(cr, uid, None, line.period_id.fiscalyear_id.id, context=context)
            ifrs_result = ifrs_line_obj._get_amount_with_operands(cr, uid,
                [line.ifrs_lines_id.ifrs_id.id],
                ifrs_line=line.ifrs_lines_id,
                period_info=period_name,
                fiscalyear=line.period_id.fiscalyear_id.id,
                number_month=dt.month,
                exchange_date=str(datetime.datetime.now().date()),
                target_move='all',
                currency_wizard=line.company_id.currency_id.id,
                context=context)

#             with open("/var/log/openerp/erp_log.txt", "a") as myfile:
#                 myfile.write("\r\nIFRS: " + str(ifrs_result) + ", Month:" + str(dt.month))

            res[line.id] = ifrs_result

        return res

    def _variance(self, cr, uid, ids, name, args, context=None):
        res = {}
        result = 0.00
        cbl_brws = self.browse(cr, uid, ids, context=context)
        res = self._get_ifrs_total(cr, uid, ids, None, None, context=context)
        for line in cbl_brws:
            if line.revenue is False:
                planned_per = self._per_netplan(cr, uid, [line.id], None, None, context=context)[line.id]
                actual_per = self._per_netactual(cr, uid, [line.id], None, None, context=context)[line.id]
                if planned_per and planned_per != 0:
                    result = (planned_per - actual_per) / planned_per
                else:
                    result = 0.00
#                 with open("/var/log/openerp/erp_log.txt", "a") as myfile:
#                     myfile.write("\r\n" + str("planned percentage 103:")+str(planned_per) + str("  --  actual percentage:")+str(actual_per) + str("  --  result:")+str(result*100))
                res[line.id] = result * 100
            else:
                ifrs_result = res[line.id]
                if ifrs_result and ifrs_result != 0:
#                    signReversedActual =  ifrs_result * -1
#                    signReversedPlan = line.planned_amount * -1
#                    result = (signReversedActual - signReversedPlan) / signReversedActual
                    result = (ifrs_result - line.planned_amount) / ifrs_result
                else:
                    result = 0.00
                     
                res[line.id] = result * 100
        return res


    def _per_netactual(self, cr, uid, ids, name, args, context=None):
        res = {}
        result = 0.0
        cbl_brws = self.browse(cr, uid, ids, context=context)
        ifrs_line_obj = self.pool.get('ifrs.lines')
        ifrs_ifrs_obj = self.pool.get('ifrs.ifrs')
        
        res = self._get_ifrs_total(cr, uid, ids, None, None, context=context)
        ifrs_result = ''
        for line in cbl_brws:
            # Calculate Net Revenue
            temp = ifrs_line_obj.search(cr, uid, [('name', '=', 'Net Revenue'), ('ifrs_id', '=', line.ifrs_lines_id.ifrs_id.id)], context=context)
            if temp:
                ifrs_line_id = temp [0]
                ifrs_line = ifrs_line_obj.browse(cr, uid, ifrs_line_id, context=context)
                
                dt = datetime.datetime.strptime(line.period_id.date_stop, '%Y-%m-%d')
                period_name = ifrs_ifrs_obj._get_periods_name_list(cr, uid, None, line.period_id.fiscalyear_id.id, context=context)
                ifrs_result = ifrs_line_obj._get_amount_with_operands(cr, uid,
                    [ifrs_line_id],
                    ifrs_line=ifrs_line,
                    period_info=period_name,
                    fiscalyear=line.period_id.fiscalyear_id.id,
                    number_month=dt.month,
                    target_move='all',
                    currency_wizard=line.company_id.currency_id.id,
                    exchange_date=str(datetime.datetime.now().date()),
                    context=context)

#             with open("/var/log/openerp/erp_log.txt", "a") as myfile:
#                 myfile.write("\r\nNet Actual: " + str(ifrs_result) + ", Month:" + str(dt.month))

#             ifrs_result = ifrs_line_obj._get_amount_value(cr, uid,
#                 [ifrs_line_id],
#                 ifrs_line=ifrs_line,
#                 period_info=line.period_id,
#                 context=context)
            
            # Calculate Current Line
            ifrs_actual = res[line.id]
            
            if ifrs_result and ifrs_result != 0:
                result = (ifrs_actual / ifrs_result) * 100
            else:
                result = 0.0
              
            res[line.id] = result
        return res
    
    def _per_netplan(self, cr, uid, ids, name, args, context=None):
        res = {}
        result = 0.0
        net_planned = 0.0
        cbl_brws = self.browse(cr, uid, ids, context=context)
        ifrs_line_obj = self.pool.get('ifrs.lines')
        for line in cbl_brws:
            ifrs_line_id = ifrs_line_obj.search(cr, uid, [('name', '=', 'Net Revenue'), ('ifrs_id', '=', line.ifrs_lines_id.ifrs_id.id)], context=context)
            if ifrs_line_id:
                budget_id = self.search(cr, uid, [('ifrs_lines_id', '=', ifrs_line_id[0])], context=context)
                if budget_id:
                    budget_line = self.browse(cr, uid, budget_id[0], context=context)
                    net_planned = budget_line.planned_amount
                else:
                    net_planned = 0.0
            else:
                net_planned = 0.0
                
            if net_planned and net_planned != 0:
                result = (line.planned_amount / net_planned) * 100
            else:
                result = 0.0
            res[line.id] = result
        return res
    
#     def _negative_var(self, cr, uid, ids, name, args, context=None):
#         res = {}
#         result = 0.00
#         cbl_brws = self.browse(cr, uid, ids, context=context)
#         for line in cbl_brws:
#             planned_per = self._per_netplan(cr, uid, [line.id], None, None, context=context)[line.id]
#             actual_per = self._per_netactual(cr, uid, [line.id], None, None, context=context)[line.id]
#             
#             if planned_per and planned_per != 0:
#                 result = (planned_per - actual_per) / planned_per
#             else:
#                 result = 0.00
#             
#             res[line.id] = result * 100
#             
#         return res
    
    def _growth_ly(self, cr, uid, ids, name, args, context=None):
        res = {}
        result = 0.00
        cbl_brws = self.browse(cr, uid, ids, context=context)
        ifrs_line_obj = self.pool.get('ifrs.lines')
        res = self._get_ifrs_total(cr, uid, ids, None, None, context=context)
        
        for line in cbl_brws:
            # Calculate Last Year Value
#             raise osv.except_osv('Error', line);
            date_to = strToDate(line.date_to)
            lasy_year_date = date_to.replace(date_to.year - 1) - timedelta(days=15)

            ifrs_line_ids = ifrs_line_obj.search(cr, uid, [('name', '=', line.ifrs_lines_id.name),
                                              ('company_id', '=', line.ifrs_lines_id.company_id.id)], context=context)
            last_budget_line_id = self.search(cr, uid, [('date_from', '<=', lasy_year_date),
                                                     ('date_to', '>=', lasy_year_date),
                                                     ('company_id', '>=', line.company_id.id),
                                                     ('ifrs_lines_id', 'in', ifrs_line_ids)], context=context)
            if last_budget_line_id:
                ifrs_result = self._get_ifrs_total(cr, uid, [last_budget_line_id[0]], None, None, context=context)[last_budget_line_id[0]]
            else:
                ifrs_result = 0.00
            
            # Calculate Growth v LY
            ifrs_actual = res[line.id]
            
            if ifrs_result and ifrs_result != 0:
                result = (ifrs_actual - ifrs_result) / ifrs_result
            else:
                result = 0.00

            res[line.id] = result * 100
        return res
    
    
    def _practical_amount_string(self, cr, uid, ids, name, args, context=None):
        res = {}
        locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        for line in self.browse(cr, uid, ids, context=context):
            temp = line.practical_amount_aa
            if temp:
#                 if line.revenue is True:
#                     temp = temp * -1
                tempString = locale.format("%d", temp, grouping=True)
            else:
                tempString = "0"
            res[line.id] = tempString
        return res
    
    def _year(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line and line.date_to:
                date_to = strToDate(line.date_to)
                mid_date = date_to - timedelta(days=15)
                res[line.id] = mid_date.year
        return res

    def _month(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line and line.date_to:
                date_to = strToDate(line.date_to)
                mid_date = date_to - timedelta(days=15)
                res[line.id] = mid_date.month
        return res

    def _quarter(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line and line.date_to:
                date_to = strToDate(line.date_to)
                mid_date = date_to - timedelta(days=15)
                quarter = (mid_date.month-1)//3 + 1
                res[line.id] = quarter
        return res
    
    def _year_month(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line and line.date_to:
                date_to = strToDate(line.date_to)
                mid_date = date_to - timedelta(days=15)
                res[line.id] = str(mid_date.year)+ str("-")+ str('%02d' % mid_date.month)
        return res

    def _year_quarter(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line and line.date_to:
                date_to = strToDate(line.date_to)
                mid_date = date_to - timedelta(days=15)
                quarter = (mid_date.month-1)//3 + 1
                res[line.id] = str(mid_date.year)+ str("-")+ str('%02d' % quarter)
        return res
    

    _order = "sequence"
    _columns = {
        'practical_amount_string': fields.function(_practical_amount_string, string='Actual Amount', type='text'),                
        'practical_amount_aa': fields.function(_get_ifrs_total,
                              string='Caused Amount', type='text',
                              digits_compute=dp.get_precision('Account'),
                              help="This amount comes from the computation related to the IFRS line report related"),
#         'practical_amount': fields.function(_prac_acc,
#                               string='Amount', type='integer',
#                               digits_compute=dp.get_precision('Account')),
#         'theoritical_amount': fields.function(_prac_acc,
#                               string='Amount', type='integer',
#                               digits_compute=dp.get_precision('Account')),
#         'forecasted_amount': fields.float('Forecasted Amount',
#                            digits_compute=dp.get_precision('Account'),
#                            help="""Due to your analisys what is the amopunt that
#                            the manager stimate will comply to be compared with
#                            the Planned Ammount"""),
#         'ifrs_lines_id': fields.many2one("ifrs.lines", "Report Line",
#         help="Line on the IFRS report to analyse your budget."),
#         'period_id': fields.many2one('account.period', 'Period',
#                                      domain=[('special', '<>', True)],
#                                      help="Period for this budget"),
#         'date_from': fields.date('Start Date'),
#         'date_to': fields.date('End Date'),
        'planned_amount_int':fields.function(_planned_amount_int, string='Planned Amount', type='text'),
        'variance':fields.function(_variance, string='Var', type='float', digits=(16,1)),
        'growth_ly':fields.function(_growth_ly, string='Growth v LY', type='float', digits=(16,1)),
        'per_netplan':fields.function(_per_netplan, string='Net Plan', type='float', digits=(16,1)),
        'per_netactual':fields.function(_per_netactual, string='Net Actual', type='float', digits=(16,1)),
        'revenue':fields.boolean('Revenue', store=True),
        'sequence': fields.integer('Sequence'),
        'year': fields.function(_year, store=True, type='integer', string="Year"),
        'month': fields.function(_month, store=True, type='integer', string="Month No#"),
        'quarter': fields.function(_quarter, store=True, type='integer', string="Quarter No#"),
        'year_month': fields.function(_year_month, store=True, type='text', string="Month"),
        'year_quarter': fields.function(_year_quarter, store=True, type='text', string="Quarter"),
    }

    _default = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'revenue': True
    }

    def write(self, cr, uid, ids, values, context=None):
        if "period_id" in values:
            period_brw = self.pool.get('account.period').browse(cr, uid, values.get('period_id'), context=context)
            values.update({'date_from': period_brw.date_start,
                           'date_to': period_brw.date_stop})
        if "ifrs_lines_id" in values:
            ifrs_line_brw = self.pool.get('ifrs.lines').browse(cr, uid, values.get('ifrs_lines_id'), context=context)
            values.update({'sequence': ifrs_line_brw.sequence})
            
        return super(crossovered_budget_lines, self).write(cr, uid, ids, values, context=context)

    def create(self, cr, uid, values, context=None):
        period_brw = self.pool.get('account.period').browse(cr, uid, values.get('period_id'), context=context)
        values.update({'date_from': period_brw.date_start,
                       'date_to': period_brw.date_stop})
        
        if "ifrs_lines_id" in values:
            ifrs_line_brw = self.pool.get('ifrs.lines').browse(cr, uid, values.get('ifrs_lines_id'), context=context)
            values.update({'sequence': ifrs_line_brw.sequence})
        
        return super(crossovered_budget_lines, self).create(cr, uid, values, context=context)

    def _prac_amt_acc(self, cr, uid, ids, context=None):
        '''
        This Method should compute considering Accounts Accounts due to the
        Account Analityc Account is not mandatory in the budget Line.
        If the account Analityc Account is empty
        '''
        res = {}
        #result = 0.0
        if context is None:
            context = {}

        cbl_brws = self.browse(cr, uid, ids, context=context)
        ifrs_line_obj = self.pool.get('ifrs.lines')
        ifrs_ifrs_obj = self.pool.get('ifrs.ifrs')
        
        for line in cbl_brws:
            dt = datetime.datetime.strptime(line.period_id.date_stop, '%Y-%m-%d')
            period_name = ifrs_ifrs_obj._get_periods_name_list(cr, uid, None, line.period_id.fiscalyear_id.id, context=context)
            ifrs_result = ifrs_line_obj._get_amount_with_operands(cr, uid,
                [line.ifrs_lines_id.ifrs_id.id],
                ifrs_line=line.ifrs_lines_id,
                period_info=period_name,
                fiscalyear=line.period_id.fiscalyear_id.id,
                number_month=dt.month,
                target_move='all',
                exchange_date=str(datetime.datetime.now().date()),
                currency_wizard=line.company_id.currency_id.id,
                context=context)
            
#             period_name = ifrs_ifrs_obj._get_periods_name_list(cr, uid, None, line.period_id.fiscalyear_id.id, context=context)
#             ifrs_result = ifrs_line_obj._get_amount_value(cr, uid,
#                 [line.ifrs_lines_id.ifrs_id.id],
#                 ifrs_line=line.ifrs_lines_id,
#                 period_info=period_name,
#                 fiscalyear=line.period_id.fiscalyear_id.id,
#                 number_month=1,
#                 currency_wizard=line.company_id.currency_id.id,
#                 context=context)
            
#             ifrs_result = ifrs_line_obj.browse(cr, uid, line.ifrs_lines_id.id).inv_sign and (-1.0 * ifrs_result) or ifrs_result
            
            res[line.id] = ifrs_result
        return res
    
    def _check_color(self, cr, uid, ids, arg, context):
        return '5';
            
        '''
        for line in self.browse(cr, uid, ids, context=context):
            date_to = line.date_to
            date_from = line.date_from
            if context.has_key('wizard_date_from'):
                date_from = context['wizard_date_from']
            if context.has_key('wizard_date_to'):
                date_to = context['wizard_date_to']
            if not date_from or not date_to:
                acc_b_ids = line.general_budget_id and line.general_budget_id.account_ids or []
                acc_ids = [x.id for x in acc_b_ids]
                if not acc_ids:
                    result = 0.00
                if line.analytic_account_id.id:
                    cr.execute("SELECT SUM(amount) FROM account_analytic_line WHERE account_id=%s AND (date "
                           "between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')) AND "
                           "general_account_id=ANY(%s)", (line.analytic_account_id.id, date_from, date_to, acc_ids,))
                    result = cr.fetchone()[0]
                else:
                    result = sum([a.balance for a in line.general_budget_id.account_ids])
            else:
                result = 0.00
            if result is None:
                result = 0.00
            res[line.id] = result
        return res
        '''
