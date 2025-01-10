from datetime import datetime, timedelta, date
from odoo.exceptions import AccessDenied, ValidationError
from odoo import models, fields, api
from odoo.fields import Command
from odoo import _
import logging
import math
from dateutil.relativedelta import relativedelta
from pytz import timezone
from lxml import etree
from odoo.exceptions import UserError
from pprint import pprint
import json
class AccountReportWizard(models.TransientModel):
    _name = 'dtsc.accountreportwizard'

    # 向导字段定义
    starttime = fields.Date('起始時間')
    endtime = fields.Date('結束時間')
    
    select_company = fields.Selection([
        ("all","全部"),
        ("not_all","非全部"),
    ],default='all' ,string="是否打印全部公司")
    company_list_customer = fields.Many2many("res.partner" , 
                                                'dtsc_accountreportwizard_customer_rel',  
                                                'wizard_id', 
                                                'partner_id', domain=[('customer_rank', '>', 0)] ,string="客戶列表")
    company_list_supplier = fields.Many2many("res.partner" ,
                                                'dtsc_accountreportwizard_supplier_rel',  
                                                'wizard_id', 
                                                'partner_id', domain=[('supplier_rank', '>', 0)],string="供應商列表")

    move_type = fields.Char("movetype")
    print_customer_label = fields.Boolean('是否打印客戶標籤')

    
    @api.onchange('select_company')
    def _compute_move_type(self):
        active_domain = self._context.get('active_domain', [])
        
        for domain_part in active_domain:
            if 'out_invoice' in domain_part:
                self.move_type = "out_invoice"
            elif 'in_invoice' in domain_part:
                self.move_type = "in_invoice"
        



    
    def your_confirm_method(self):
    
        # print(self._context)
        docids = []
        docs = self.env['account.move'].browse(docids)
        company_ids = []
        if self.move_type == "out_invoice":
            for record in self.company_list_customer:
                company_ids.append(record.id)
        elif self.move_type == "in_invoice":
            for record in self.company_list_supplier:
                company_ids.append(record.id)
        
        data = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'company_id': company_ids,
            'docids':docids,
            'select_company':self.select_company,
            "docs":docs,
            'doc_model': 'account.move',
            'print_customer_label': self.print_customer_label,
        }
        print(data)
        return self.env.ref('dtsc.dtsc_invoices').report_action(docids,data)
        
class AccountReport(models.AbstractModel):
    _name = 'report.dtsc.report_invoice_template'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        
        
        print("================")
        context = data.get('context', {})
        move_type = context.get('default_move_type')
        docids = data.get('docids', docids)
        company_ids = data.get('company_id', None)
        select_company = data.get('select_company', None)
        
        if company_ids:
            print(company_ids)
        else:
            print("No company_id provided")   

        start_date = data.get('starttime')
        end_date = data.get('endtime')
        print("================")
        if not start_date:
            docs = self.env['account.move'].browse(docids)
            
            # company_id = docs[0].company_id
            partner_id = docs[0].partner_id
            # print(company_id.id)
            print(partner_id.id)
            # for order in docs:
                # if order.company_id != company_id:
                    # raise UserError("只能打印同一家公司的單據！")
                    
            for order in docs:
                if order.partner_id != partner_id:
                    raise UserError("只能打印同一家公司的單據！")       
            print(partner_id.is_supplier)
            print(partner_id.is_customer)
            if partner_id.is_supplier == True:
                move_type = "in_invoice"
            elif partner_id.is_customer == True:
                move_type = "out_invoice"
            
        print(move_type)
        data["company_details"] = []
        if move_type == "out_invoice":
            if not start_date:
                company_detail = {
                    'title_name' : "對賬單",
                    'move_type' : "out_invoice",
                    'company_name' : docs[0].partner_id.name,
                    'address': docs[0].partner_id.street,
                    'phone': docs[0].partner_id.phone,
                    'custom_invoice_form': docs[0].partner_id.custom_invoice_form,
                    'vat': docs[0].partner_id.vat,
                    'custom_contact_person': docs[0].partner_id.custom_contact_person,
                    'user_id': docs[0].partner_id.user_id.name,
                    'receive_mode': docs[0].partner_id.custom_pay_mode,
                    'invoice_ids':[],
                    'custom_id':docs[0].partner_id.custom_id,  
                }
                
                for record in docs:
                    for line in record.invoice_line_ids:
                        # 添加发票行信息
                        line_detail = {
                            "date" : record.invoice_date,
                            "in_out_id" : line.in_out_id,
                            "ys_name" : line.ys_name,
                            "size_value" : line.size_value,
                            "comment" : line.comment,
                            "quantity_show" : line.quantity_show,
                            "price_unit_show" : line.price_unit_show,
                            "make_price" : line.make_price,
                            "price_subtotal" : line.price_subtotal,
                        }
                        company_detail["invoice_ids"].append(line_detail)
                
                data["company_details"].append(company_detail)
            else:
                if select_company not in ["not_all"]:
                    company_id_list = self.env['res.partner'].search([('customer_rank', '>', 0)])
                    company_ids = company_id_list.mapped("id")
                for company_id in company_ids:  # 外层循环处理每个 company_id
                    company = self.env['res.partner'].browse(company_id)
                    if company.exists():
                        all_records = self.env["account.move"].search([
                                ('partner_id', '=', company_id),
                                ('invoice_date', '>=', start_date),   # 起始日期
                                ('invoice_date', '<=', end_date),  
                                ('move_type', 'in', ['out_invoice']),
                                ],order='invoice_date asc')
                
                        company_records = all_records.filtered(lambda r: r.partner_id.id == company_id)
                
                        if not company_records:
                            continue
               
                        company_detail = {
                                    'title_name' : "對賬單",
                                    'move_type' : "out_invoice",
                                    'company_name' : company.name,
                                    'address': company.street,
                                    'phone': company.phone,
                                    'custom_invoice_form': company.custom_invoice_form,
                                    'vat': company.vat,
                                    'custom_contact_person': company.custom_contact_person,
                                    'user_id': company.user_id.name,
                                    'receive_mode': company.custom_pay_mode,
                                    'invoice_ids':[],
                                    'custom_id':company.custom_id,  
                                }
                
                        for record in company_records:
                            for line in record.invoice_line_ids:
                                # 添加发票行信息
                                line_detail = {
                                    "date" : record.invoice_date,
                                    "in_out_id" : line.in_out_id,
                                    "ys_name" : line.ys_name,
                                    "size_value" : line.size_value,
                                    "comment" : line.comment,
                                    "quantity_show" : line.quantity_show,
                                    "price_unit_show" : line.price_unit_show,
                                    "make_price" : line.make_price,
                                    "price_subtotal" : line.price_subtotal,
                                }
                                company_detail["invoice_ids"].append(line_detail)
                        
                        data["company_details"].append(company_detail)
                   
        else:
            #tree頁面直接勾選打印
            if not start_date:
                company_detail = {
                    'title_name' : "應付單",
                    'move_type' : "in_invoice",
                    'company_name' : docs[0].partner_id.name,
                    'street': docs[0].partner_id.street,
                    'phone': docs[0].partner_id.phone,
                    'custom_fax': docs[0].partner_id.custom_fax,
                    'invoice_person': docs[0].partner_id.invoice_person,
                    'invoice_ids':[],
                }
                in_out_id = ""
                for record in docs:
                    if record.invoice_origin:
                        in_out_id = record.invoice_origin
                    a = 1
                    for line in record.invoice_line_ids:
                        # 添加发票行信息
                        text = line.name
                        if ":" in text:
                            aaa, ys_name = text.split(":", 1)
                        else:
                            # in_out_id = ""
                            ys_name = line.name
                        if in_out_id:
                           in_out_id = in_out_id + "-" + str(a)
                        line_detail = {
                            "date" : record.invoice_date,
                            "in_out_id" : in_out_id,
                            "ys_name" : ys_name,
                            
                            "quantity" : line.quantity,
                            "product_uom_id" : line.product_uom_id.name,
                            "price_unit" : line.price_unit,
                            "price_subtotal" : line.price_subtotal,
                        }
                        a = a + 1
                        company_detail["invoice_ids"].append(line_detail)
                
                data["company_details"].append(company_detail)
            else:
                if select_company not in ["not_all"]:
                    company_id_list = self.env['res.partner'].search([('supplier_rank', '>', 0)])
                    company_ids = company_id_list.mapped("id")
                    print(company_ids)
                for company_id in company_ids:  # 外层循环处理每个 company_id
                    company = self.env['res.partner'].browse(company_id)
                    if company.exists():
                        all_records = self.env["account.move"].search([
                                ('partner_id', '=', company_id),
                                ('invoice_date', '>=', start_date),   # 起始日期
                                ('invoice_date', '<=', end_date),  
                                ('move_type', 'in', ['in_invoice']),
                                ],order='invoice_date asc')
                
                        company_records = all_records.filtered(lambda r: r.partner_id.id == company_id)
                
                        if not company_records:
                            continue
               
                        company_detail = {
                                    'title_name' : "應付單",
                                    'move_type' : "in_invoice",
                                    'company_name' : company.name,
                                    'street': company.street,
                                    'phone': company.phone,
                                    'custom_fax': company.custom_fax,
                                    'invoice_person': company.invoice_person,
                                    'invoice_ids':[],
                                }
                        in_out_id = ""
                        for record in company_records:
                            if record.invoice_origin:
                                in_out_id = record.invoice_origin
                            a = 1
                            for line in record.invoice_line_ids:
                                # 添加发票行信息
                                text = line.name
                                if ":" in text:
                                    aaa, ys_name = text.split(":", 1)
                                else:
                                    # in_out_id = ""
                                    ys_name = line.name
                                if in_out_id:
                                   in_out_id = in_out_id + "-" + str(a)
                                line_detail = {
                                    "date" : record.invoice_date,
                                    "in_out_id" : in_out_id,
                                    "ys_name" : ys_name,
                                    
                                    "quantity" : line.quantity,
                                    "product_uom_id" : line.product_uom_id.name,
                                    "price_unit" : line.price_unit,
                                    "price_subtotal" : line.price_subtotal,
                                }
                                a = a + 1
                                company_detail["invoice_ids"].append(line_detail)
                        
                        data["company_details"].append(company_detail)
        
        docs = self.env['account.move'].browse(docids)
        
       
        print(data)
        
        company = self.env['res.company']._company_default_get('account.move')
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'company': company,
            'data': data,
        }