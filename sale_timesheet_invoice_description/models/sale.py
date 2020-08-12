# -*- coding: utf-8 -*-
# © 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models, _
from openerp.tools import config
import time

import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_invoice_description = fields.Selection(
        '_get_timesheet_invoice_description', default='000')

    @api.model
    def _get_timesheet_invoice_description(self):
        return [
            ('000', _('None')),
            ('111', _('Date - Time spent - Description')),
            ('101', _('Date - Description')),
            ('001', _('Description')),
            ('011', _('Time spent - Description')),
        ]


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_invoice_line_details(self, line, desc_rule):
        details = []
        if desc_rule[0] == '1':
            user_lang = self.env['res.lang'].search([('code','=', self.env.user.lang)], limit=1)
            date_format = user_lang[0] and user_lang[0].date_format or '%Y-%m-%d'
            details.append(time.strftime(date_format, time.strptime(line.date, '%Y-%m-%d')))
        if desc_rule[1] == '1':
            if self.env.ref('product.product_uom_hour').id == line.product_uom_id.id:
                details.append('{0:02.0f}:{1:02.0f}'.format(*divmod(line.unit_amount * 60, 60)))
            else:
                details.append("%s %s" % (line.unit_amount, line.product_uom_id.name))
        if desc_rule[2] == '1':
            details.append(line.name)
        return details

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        desc_rule = self.order_id.timesheet_invoice_description
        if not desc_rule or desc_rule == '000':
            return res
        note = []
        domain = [('so_line', '=', self.id)]
        last_invoice = self.invoice_lines.sorted(lambda x: x.create_date)[-1:]
        if last_invoice:
            domain.append(('create_date', '>', last_invoice.create_date))
        for line in self.env['account.analytic.line'].search(domain, order='date, id'):
            details = self._prepare_invoice_line_details(line, desc_rule)
            note.append(u' - '.join(map(lambda x: unicode(x) or '', details)))
        # This is for not breaking possible tests that expects to create the
        # invoices lines the standard way
        if note and (not config['test_enable'] or self.env.context.get('timesheet_description')):
            res['name'] += "\n" + ("\n".join(map(lambda x: unicode(x) or '', note)))
        return res
