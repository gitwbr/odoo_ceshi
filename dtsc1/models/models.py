#!/usr/bin/python3
# @Time    : 2021-11-23
# @Author  : Kevin Kong (kfx2007@163.com)

from datetime import datetime, timedelta, date
from odoo.exceptions import AccessDenied, ValidationError
from odoo import models, fields, api ,_
from odoo.fields import Command
import logging
from dateutil.relativedelta import relativedelta
import re
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)
from odoo.tools.float_utils import float_compare, float_is_zero, float_round



class Book(models.Model):

    _name = 'dtsc.book'
    _description = "图书"

    name = fields.Char('名称', help="书名")
    price = fields.Float("定价", help="定价")
    
class UserType(models.Model):

    _name = 'dtsc.usertype'
    
    name = fields.Char(string = "工種")
   

class UserListBefore(models.Model):

    _name = 'dtsc.reworklist'
    
    name = fields.Char(string = "師傅")   

class UserListBefore(models.Model):

    _name = 'dtsc.userlistbefore'
    
    name = fields.Char(string = "師傅")
    # worktype_ids = fields.Many2many('dtsc.usertype', string="工種")
  
class UserList(models.Model):

    _name = 'dtsc.userlist'
    
    name = fields.Char(string = "師傅")
    worktype_ids = fields.Many2many('dtsc.usertype', string="工種")
  
    
class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"
    
    _sql_constraints = [
        ('name_uniq' , 'unique(name,attribute_id)' , _('不能使用重復的變體名'))
    ]
    
    def write(self, vals):
        # 调用父类的 write 方法更新当前记录
        res = super(ProductAttributeValue, self).write(vals)

        # 如果 sequence 字段被更新，则同步更新相关的 product.template.attribute.value 记录
        if 'sequence' in vals:
            # 获取所有相关的 product.template.attribute.value 记录
            template_attr_values = self.env['product.template.attribute.value'].search([
                ('product_attribute_value_id', 'in', self.ids)
            ])

            # 更新这些记录的 sequence 字段
            for template_attr_value in template_attr_values:
                template_attr_value.write({'sequence': vals['sequence']})

        return res
    
class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'
    _order = 'sequence'
    
    sequence = fields.Integer(string="Sequence")
    
    @api.model
    def create(self, vals):
        attribute_value_id = vals.get('product_attribute_value_id')
        if attribute_value_id:
            # 获取对应的 product.attribute.value 记录
            attribute_value = self.env['product.attribute.value'].browse(attribute_value_id)

            # 从 product.attribute.value 记录中获取 sequence 值
            sequence = attribute_value.sequence

            # 设置 sequence 值到新记录的 vals 中
            vals['sequence'] = sequence
        return super(ProductTemplateAttributeValue, self).create(vals)

class Billdate(models.TransientModel):
    _name = 'dtsc.billdate'
    _description = '賬單日期'

    selected_date = fields.Date(string='賬單日期')
    
    def action_confirm(self):
        active_ids = self._context.get('active_ids')
        records = self.env["purchase.order"].browse(active_ids)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        partner_id = records[0].partner_id
        if any(order.partner_id != partner_id for order in records):
            raise UserError("只能合併同一家公司的採購單！")
        
        # effective_dates = self.mapped('effective_date')
        # earliest_date = min(effective_dates) if effective_dates else None

        # 1) Prepare combined invoice vals
        combined_invoice_vals = {
            'invoice_line_ids': [],
            'company_id': None,
            'partner_id': None,
            'currency_id': None,
            'invoice_origin': '',
            'payment_reference': '',
            'move_type': 'in_invoice',
            'invoice_date': self.selected_date,
            'ref': '',
        }
        origins = set()
        payment_refs = set()
        refs = set()

        for order in records:
            if order.invoice_status != 'to invoice':
                raise UserError("%s 還不能轉應付賬單！請檢查！" %order.name)

            order = order.with_company(order.company_id)
            invoice_vals = order._prepare_invoice()
            combined_invoice_vals['company_id'] = invoice_vals['company_id']
            combined_invoice_vals['partner_id'] = invoice_vals['partner_id']
            combined_invoice_vals['currency_id'] = invoice_vals['currency_id']
            
            for line in order.order_line:
                if line.display_type != 'line_section' and not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    line_vals = line._prepare_account_move_line()
                    combined_invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

            origins.add(invoice_vals['invoice_origin'])
            payment_refs.add(invoice_vals['payment_reference'])
            refs.add(invoice_vals['ref'])
            order.write({'my_state': '4'})

        combined_invoice_vals.update({
            'invoice_origin': ', '.join(origins),
            'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            'ref': ', '.join(refs)[:2000],
        })

        # 2) Create the combined invoice.
        if not combined_invoice_vals['invoice_line_ids']:
            raise UserError(_('There is no invoiceable line.'))

        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        move = AccountMove.with_company(combined_invoice_vals['company_id']).create(combined_invoice_vals)

        for order in records:
            order.invoice_origin = move.id

        # 3) Convert to refund if total amount is negative
        if move.currency_id.round(move.amount_total) < 0:
            move.action_switch_invoice_into_refund_credit_note()

        return self.env["purchase.order"].action_view_invoice(move)


        

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        super_result = super(StockPicking, self).button_validate()

        if super_result == True:
            order = self.env["purchase.order"].search([('name' ,"=" ,self.origin)])
            if order:
                order.write({'my_state': '3'})

        return super_result

    @api.model
    def default_get(self, fields):
        res = super(StockPicking, self).default_get(fields)
        picking_type_code = self.env.context.get('default_picking_type_id')
        print(1111111111111)
        print(picking_type_code)
        # 获取当前操作类型的编码
        if picking_type_code:
            picking_type = self.env['stock.picking.type'].browse(picking_type_code)
            if picking_type.code == 'internal':
                print(222222)
                res['partner_id'] = 1  # 设置一个你想要的默认 partner_id
        return res
        
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    my_state = fields.Selection([
        ('1', '詢價單'),
        ('2', '待收貨'),
        ('3', '未轉應付'),
        ('4', '已轉應付'),
        ('5', '作廢'),
    ], string='狀態', default='1')
    partner_display_name = fields.Char(string='Partner Display Name', compute='_compute_partner_display_name' ,store=True)
    custom_id = fields.Char(related = "partner_id.custom_id",string="供應商編號")
    invoice_origin = fields.Many2one("account.move")
    is_return_goods = fields.Boolean("退貨單")
    return_goods_comment = fields.Char("退貨備註")
    search_line = fields.Char(compute="_compute_search_line_project_product_name", store=True)
    purchase_comment = fields.Text("備註")
    
    @api.depends("order_line.name","order_line.product_id","name","partner_id")
    def _compute_search_line_project_product_name(self):
        for record in self:
            names = [line.name for line in record.order_line if line.name]
            product_names = [line.product_id.name for line in record.order_line if line.product_id.name]

            
            combined_names = ', '.join(names)
            combined_product_names = ', '.join(product_names)

            
            result = ', '.join([
                combined_names or '', combined_product_names or '', record.name or '' , record.partner_id.name or ''
            ])
            
            #print(result)
            
            record.search_line = result    
   
    def go_to_zuofei(self):
        self.write({'my_state': '5'})
        
    
    
    def action_create_invoice_muti(self):
        active_ids = [] 
        for order in self:
            active_ids.append(order.id)
    
        # reference_datetime = records[0].estimated_date
        view_id = self.env.ref('dtsc.view_dtsc_deliverydate_form').id
        return {
            'name': '選擇賬單日期',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'dtsc.billdate',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {'default_selected_date': fields.Date.today(), 'active_ids': active_ids},
        }    
        

    @api.depends("partner_id")
    def _compute_partner_display_name(self):
        # print("_compute_partner_display_name")
        for record in self:
            # print(record.partner_id.custom_id)
            # print(record.partner_id.name)
            if record.partner_id:
                record.partner_display_name = f"{record.partner_id.custom_id}, {record.partner_id.name}"
                
    def button_approve(self, force=False):
        res = super(PurchaseOrder, self).button_approve(force=force)
        self.write({'my_state': '2'})
        return res
 
    def action_create_invoice(self, force=False):
        action = super(PurchaseOrder, self).action_create_invoice()

        # 检查是否生成了账单并且存在有效日期
        if action and 'res_id' in action and self.effective_date:
            # 获取账单记录的ID
            invoice_id = action['res_id']

            # 使用 browse 获取账单记录并更新日期
            self.env['account.move'].browse(invoice_id).write({
                'invoice_date': self.effective_date
            })

        # 更新状态
        self.write({'my_state': '4'})
        self.write({"invoice_origin" : invoice_id})
        return action                

class DtscConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_due_date = fields.Integer(string="賬單日")
    
    ftp_server = fields.Char("FTP地址")
    ftp_user = fields.Char("FTP用戶名")
    ftp_password = fields.Char("FTP密碼")
    ftp_target_folder = fields.Char("FTP目標文件夾")
    ftp_local_path = fields.Char("FTP本地路徑")
    
    # ftp_server = self.env['ir.config_parameter'].sudo().get_param('dtsc.ftp_server')
    # ftp_user = self.env['ir.config_parameter'].sudo().get_param('dtsc.ftp_user')
    # ftp_password = self.env['ir.config_parameter'].sudo().get_param('dtsc.ftp_password')
    # ftp_target_folder = self.env['ir.config_parameter'].sudo().get_param('dtsc.ftp_target_folder')
    # ftp_local_path = self.env['ir.config_parameter'].sudo().get_param('dtsc.ftp_local_path')
    
    
    
    @api.model
    def get_values(self):
        res = super(DtscConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            invoice_due_date=get_param('dtsc.invoice_due_date', default='25'),
            ftp_server=get_param('dtsc.ftp_server', default=''),
            ftp_user=get_param('dtsc.ftp_user', default=''),
            ftp_password=get_param('dtsc.ftp_password', default=''),
            ftp_target_folder=get_param('dtsc.ftp_target_folder', default='/Home'),
            ftp_local_path=get_param('dtsc.ftp_local_path', default='/var/www/html/ftp'),
        )
        return res

    def set_values(self):
        super(DtscConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('dtsc.invoice_due_date', self.invoice_due_date)
        set_param('dtsc.ftp_server', self.ftp_server)
        set_param('dtsc.ftp_user', self.ftp_user)
        set_param('dtsc.ftp_password', self.ftp_password)
        set_param('dtsc.ftp_target_folder', self.ftp_target_folder)
        set_param('dtsc.ftp_local_path', self.ftp_local_path)