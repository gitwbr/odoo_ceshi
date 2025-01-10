from odoo import models, fields, api 
import datetime
import logging
_logger = logging.getLogger(__name__)


class DeliveryOrder(models.Model):
    _name = 'dtsc.deliveryorder'
    _order = 'order_date desc'
    install_state = fields.Selection([
        ("draft","草稿"),
        ("installing","已發送"),
        ("cancel","作廢"),    
    ],default='draft' ,string="狀態")
    name = fields.Char(string='單號')
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    customer = fields.Many2one('res.partner',string='客戶名稱',readonly=True)
    contact_person = fields.Char(related="customer.custom_contact_person",string='聯絡人')
    delivery_method = fields.Char(string='交貨方式')
    phone = fields.Char(related="customer.phone",string='電話')
    fax = fields.Char(related="customer.custom_fax",string='傳真')
    checkout_ids = fields.Many2many("dtsc.checkout",string='傳真')
    factory = fields.Char(string='工廠')
    order_date = fields.Date(string='進單時間') 
    delivery_date = fields.Datetime(string='交貨時間')
    speed_type = fields.Selection([
        ('normal', '正常'),
        ('urgent', '急件')
    ], string='速別',default='normal')
    order_ids = fields.One2many("dtsc.deliveryorderline","make_order_id")
    project_name = fields.Char(string='案名')
    comment = fields.Char(string='備註') 
    factory_comment = fields.Char(string='廠區備註') 
    total_quantity = fields.Integer(string='本單總數量', compute='_compute_totals')
    total_size = fields.Integer(string='本單總才數', compute='_compute_totals')
    
    
    @api.model
    def get_26_to_25_dates(self):
        """计算日期范围，从26号到下个月25号或从上个月26号到本月25号"""
        today = fields.Date.context_today(self)
        year = today.year
        month = today.month

        if today.day > 25:
            # 本月26号到下个月25号
            start_date = today.replace(day=26)
            if month == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
            end_date = datetime.date(next_year, next_month, 25)
        else:
            # 上月26号到本月25号
            if month == 1:
                last_month = 12
                last_year = year - 1
            else:
                last_month = month - 1
                last_year = year
            start_date = fields.Date.from_string(f"{last_year}-{last_month:02d}-26")
            end_date = today.replace(day=25)

        return {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }

    @api.model
    def action_window_deliveryorder(self):
        """返回带动态上下文的Action"""
        action = self.env.ref('dtsc.action_window_deliveryorder').read()[0]
        dates = self.get_26_to_25_dates()
        action['context'] = {
            'default_start_date': dates['start_date'],
            'default_end_date': dates['end_date'],
            'search_default_custom_26_to_25': 1
        }
        _logger = logging.getLogger(__name__)
        _logger.info("Action Context: %s", action['context'])
        return action
    
    @api.depends('order_ids.quantity','order_ids.total_size')
    def _compute_totals(self):
        for record in self:
            total_quantity = sum(line.quantity for line in record.order_ids)
            total_size = sum(line.total_size for line in record.order_ids)
            
            record.total_quantity = total_quantity
            record.total_size = total_size 
    def send_install_list(self):
        print("send_install_list")  
        
    def del_install_list(self):
        records = self.env["dtsc.checkout"].search([('delivery_order' ,"=" ,self.name)])
        
        for record in records:
            record.write({'is_delivery': False})
            record.write({'delivery_order': ""})
            record.write({'checkout_order_state': "finished"})
            
        self.write({"install_state":"cancel"})         
        self.write({"name":self.name+"-D"})
    
    def unlink(self):
        checkout_records = self.mapped('checkout_ids')
        for record in checkout_records:
            record.write({'is_delivery': False})
            record.write({'delivery_order': ""})
            record.write({'checkout_order_state': "finished"})
        return super(DeliveryOrder, self).unlink()
    
class DeliveryOrderLine(models.Model):
    _name = 'dtsc.deliveryorderline'
    sequence = fields.Char(string='項')
    make_order_id = fields.Many2one("dtsc.deliveryorder",ondelete='cascade')
    
    file_name = fields.Char(string='檔名/品名')
    quantity = fields.Integer(string='數量')
    product_width = fields.Char(string='寬') 
    product_height = fields.Char(string='高')
    size = fields.Float("才")     
    total_size = fields.Float("總才數",compute="_compute_total_size")     
    machine_id = fields.Many2one("dtsc.machineprice",string="生產機台")
    multi_chose_ids = fields.Char(string='後加工名稱')
    product_atts = fields.Many2many("product.attribute.value",string="屬性名稱" )
    comment = fields.Char(string='客戶備註') 
    product_id = fields.Many2one("product.template",string='商品名稱' ,required=True)  
    make_orderid = fields.Char("製作單號")
    processing_method = fields.Text(string='加工方式', compute='_compute_processing_method')
    output_material = fields.Char(string='輸出材質', compute='_compute_output_material')
    production_size = fields.Char(string='製作尺寸', compute='_compute_production_size')
    lengbiao = fields.Char(string='裱', compute='_compute_lengbiao')
    
    
    @api.depends('product_id', 'product_atts')
    def _compute_lengbiao(self):
        for record in self:
            attributes = []
            cold_laminated_values = [att.name for att in record.product_atts if att.attribute_id.name == '冷裱']
            attributes.extend(cold_laminated_values)
            if cold_laminated_values:
                if ''.join(attributes) == "不護膜":
                    record.lengbiao = "X"
                else:
                    record.lengbiao = ''.join(attributes)
            else:
                record.lengbiao = "X"
    
    @api.depends('size','quantity') 
    def _compute_total_size(self):
        for record in self:
            record.total_size = record.size #* record.quantity
            
    @api.depends('product_width', 'product_height', 'size')
    def _compute_production_size(self):
        for record in self:
            record.production_size = record.product_width + "X" + record.product_height #+ "(" + str(record.size) + ")"
    
    @api.depends('multi_chose_ids', 'product_atts')
    def _compute_processing_method(self):
        for record in self:
            att_lines = []
            for att in record.product_atts:
                if att.attribute_id.name != "冷裱" and att.attribute_id.name != "機台" and att.attribute_id.name != "印刷方式":
                    # 获取属性名和属性值，并组合
                    att_lines.append(f'{att.attribute_id.name}：{att.name}')
            
            if record.multi_chose_ids and record.multi_chose_ids != '[]':
                att_lines.append(f'後加工：{record.multi_chose_ids}')
            
            # 合并属性行
            combined_value = '/'.join(att_lines)
            record.processing_method = combined_value
            
    @api.depends('machine_id', 'product_id', 'product_atts')
    def _compute_output_material(self):
        for record in self:
            attributes = []
            
            # 添加machine_id的name
            if record.machine_id:
                attributes.append(record.machine_id.name)
            
            # 添加product_id的name
            if record.product_id:
                attributes.append(record.product_id.name)
            
            # 查找屬於“冷裱”的product_atts的值，并添加
            # cold_laminated_values = [att.name for att in record.product_atts if att.attribute_id.name == '冷裱']
            # attributes.extend(cold_laminated_values)
            # 查找屬於“印刷方式”的product_atts的值，并添加
            cold_laminated_values = [att.name for att in record.product_atts if att.attribute_id.name == '印刷方式']
            attributes.extend(cold_laminated_values)
            
            # 使用'-'连接所有属性
            combined_value = '-'.join(attributes)
            record.output_material  = combined_value
 
class ReportDeliveryOrder(models.AbstractModel):
    _name = 'report.dtsc.report_deliveryorder_template'
    _description = 'Description for DeliveryOrder Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['dtsc.deliveryorder'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'dtsc.deliveryorder',
            'docs': docs,
        }
