from odoo import models, fields, api 

from odoo.exceptions import UserError
 


class MakeOut(models.Model):
    _name = 'dtsc.makeout'
    _order = "checkout_order_date desc"
    install_state = fields.Selection([
        ("draft","草稿"),
        ("installing","製作中"),
        ("succ","完成"),
        ("cancel","作廢"),    
    ],default='draft' ,string="狀態")
    name = fields.Char(string='單號')
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    customer_name = fields.Char(string='客戶名稱')
    contact_person = fields.Char(string='聯絡人')
    delivery_method = fields.Char(string='交貨方式')
    phone = fields.Char(string='電話')
    fax = fields.Char(string='傳真')
    factory = fields.Char(string='工廠')
    order_date = fields.Date(string='進單時間') 
    checkout_id = fields.Many2one('dtsc.checkout')
    user_id = fields.Many2one("res.users", string="業務" , related="checkout_id.user_id")
    is_recheck = fields.Boolean(related="checkout_id.is_recheck",string="是否是重置單")
    source_name = fields.Char(related="checkout_id.source_name",string="來源賬單")
    recheck_user = fields.Many2many(related="checkout_id.recheck_user",string="重製相關人員")
    recheck_comment = fields.Char(related="checkout_id.recheck_comment",string="重製備註說明")
    recheck_groups = fields.Many2many(related="checkout_id.recheck_groups",string="重製相關部門") 
    
    delivery_date = fields.Datetime(related="checkout_id.estimated_date" ,string='發貨日期' ,readonly=False,inverse='_inverse_delivery_date')
    delivery_date_show = fields.Datetime(string='發貨日期', compute="_compute_delivery_date_show",store=True)
    checkout_order_date = fields.Datetime(string='大圖訂單時間')
    speed_type = fields.Selection([
        ('normal', '正常'),
        ('urgent', '急件')
    ], string='速別',default='normal')
    order_ids = fields.One2many("dtsc.makeoutline","make_order_id")
    project_name = fields.Char(string='案名')
    comment = fields.Char(string='客戶備註') 
    factory_comment = fields.Char(string='廠區備註') 
    total_quantity = fields.Integer(string='本單總數量', compute='_compute_totals')
    total_size = fields.Integer(string='本單總才數', compute='_compute_totals')
    supplier_id = fields.Many2one('res.partner', string='委外商', domain=[('supplier_rank', '>', 0)])
    pinguanman = fields.Many2many('dtsc.userlist',string="品管" , domain=[('worktype_ids' , 'in' , [3])])
    create_id = fields.Many2one('res.users',string="開單人員")
     

    
     
    @api.depends("delivery_date")
    def _compute_delivery_date_show(self):
        for record in self:
           record.delivery_date_show = record.delivery_date 
    
    def _inverse_delivery_date(self):
        for record in self:
            record.checkout_id.estimated_date = record.delivery_date
    
    @api.depends('order_ids.quantity','order_ids.total_size')
    def _compute_totals(self):
        for record in self:
            total_quantity = sum(line.quantity for line in record.order_ids)
            total_size = sum(line.total_size for line in record.order_ids)
            
            record.total_quantity = total_quantity
            record.total_size = total_size 
    def send_install_list(self):
        self.write({"install_state":"installing"}) 
        
    def btn_send(self):
        if not self.pinguanman:
            raise UserError("請錄入品管員工！")
        if not self.supplier_id:
            raise UserError("請錄入委外商！")
        
        self.write({"install_state":"succ"}) 
        

        
    def del_install_list(self):
        self.write({"install_state":"cancel"})     
        self.write({"name":self.name+"-D"})

class MakeLine(models.Model):
    _name = 'dtsc.makeoutline'
    sequence = fields.Char(string='項')
    make_order_id = fields.Many2one("dtsc.makeout",ondelete='cascade')
    
    file_name = fields.Char(string='檔名')    
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
    quantity_peijian = fields.Float("配件數") 
    processing_method = fields.Text(string='加工方式', compute='_compute_processing_method')
    lengbiao = fields.Char(string='裱', compute='_compute_lengbiao')
    output_material = fields.Char(string='輸出材質', compute='_compute_output_material')
    production_size = fields.Char(string='製作尺寸', compute='_compute_production_size')
    
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
            record.production_size = record.product_width + "*" + record.product_height #+ "(" + str(record.size) + ")"
    
    @api.depends('multi_chose_ids', 'product_atts')
    def _compute_processing_method(self):
        for record in self:
            att_lines = []
            for att in record.product_atts:
                if att.attribute_id.name != "冷裱" and att.attribute_id.name != "機台" and att.attribute_id.name != "印刷方式":
                    # 获取属性名和属性值，并组合
                    # att_lines.append(f'{att.attribute_id.name}：{att.name}')
                    if att.attribute_id.name == "配件":
                        att_lines.append(f'{att.name}({round(record.quantity_peijian)})')
                    else:
                        att_lines.append(f'{att.name}')
            
            if record.multi_chose_ids and record.multi_chose_ids != '[]':
                att_lines.append(f'{record.multi_chose_ids}')
            
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
 
class ReportMakeout(models.AbstractModel):
    _name = 'report.dtsc.report_makeout_template'
    _description = 'Description for Makeout Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['dtsc.makeout'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'dtsc.makeout',
            'docs': docs,
        }
