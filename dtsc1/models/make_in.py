from odoo import models, fields, api 
import math
import base64
import requests
import json
from odoo.exceptions import UserError
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from PIL import Image
import base64
import qrcode
from datetime import datetime, timedelta 
import logging
_logger = logging.getLogger(__name__)


class MakeIn(models.Model):
    _name = 'dtsc.makein'
    _order = "checkout_order_date desc"
    install_state = fields.Selection([
        ("draft","草稿"),
        # ("imageing","審圖"),
        ("imaged","工單已審"),
        ("making","製作中"),    
        ("stock_in","完成製作"),    
        ("cancel","作廢"),    
    ],default='draft' ,string="狀態")
    name = fields.Char(string='單號')
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    display_name = fields.Char(related="company_id.display_name", string='公司')
    checkout_id = fields.Many2one('dtsc.checkout')
    user_id = fields.Many2one("res.users", string="業務" , related="checkout_id.user_id")
    is_recheck = fields.Boolean(related="checkout_id.is_recheck",string="是否是重置單")
    source_name = fields.Char(related="checkout_id.source_name",string="來源賬單")
    recheck_user = fields.Many2many(related="checkout_id.recheck_user",string="重製相關人員")
    recheck_comment = fields.Char(related="checkout_id.recheck_comment",string="重製備註說明")
    recheck_groups = fields.Many2many(related="checkout_id.recheck_groups",string="重製相關部門") 
    
    customer_name = fields.Char(string='客戶名稱')
    contact_person = fields.Char(string='聯絡人')
    delivery_method = fields.Char(string='交貨方式')
    phone = fields.Char(string='電話')
    fax = fields.Char(string='傳真')
    factory = fields.Char(string='工廠')
    order_date = fields.Date(string='進單時間') 
    # delivery_date = fields.Datetime(related="checkout_id.estimated_date" ,string='發貨日期' )
    delivery_date = fields.Datetime(related="checkout_id.estimated_date" ,string='發貨日期' ,readonly=False,inverse='_inverse_delivery_date')
    delivery_date_show = fields.Datetime(string='發貨日期', compute="_compute_delivery_date_show",store=True)
    checkout_order_date = fields.Datetime(string='大圖訂單時間')
    speed_type = fields.Selection([
        ('normal', '正常'),
        ('urgent', '急件')
    ], string='速別',default='normal')
    order_ids = fields.One2many("dtsc.makeinline","make_order_id")
    project_name = fields.Char(string='案名')
    comment = fields.Char(string='客戶備註') 
    factory_comment = fields.Char(string='廠區備註') 
    total_quantity = fields.Integer(string='本單總數量', compute='_compute_totals')
    total_size = fields.Integer(string='本單總才數', compute='_compute_totals')
    create_id = fields.Many2one('res.users',string="開單人員")
    kaidan = fields.Many2one('dtsc.userlistbefore',string="開單人員")
    no_mprlist = fields.Boolean(default=False)
    
    #1輸出 2後置 3品管 4其他
    houzhiman = fields.Many2many('dtsc.userlist','dtsc_makein_dtsc_userlist_rel1', 'dtsc_makein_id','dtsc_userlist_id',string="後製" , domain=[('worktype_ids' , 'in' , [2])])
    pinguanman = fields.Many2many('dtsc.userlist','dtsc_makein_dtsc_userlist_rel2', 'dtsc_makein_id','dtsc_userlist_id',string="品管" , domain=[('worktype_ids' , 'in' , [3])])
    outmanall = fields.Many2one('dtsc.userlist',string="所有輸出" , domain=[('worktype_ids' , 'in', [1])])
    
    @api.model
    def get_26_to_25_dates(self):
        """通用的日期选择方法：从26号到下个月25号或上个月26号到本月25号"""
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

        # 返回日期范围作为上下文
        return {
            'default_start_date': start_date.strftime('%Y-%m-%d'),
            'default_end_date': end_date.strftime('%Y-%m-%d')
        }
    
    
    @api.model
    def action_set_26_to_25_dates(self):
        # 调用通用的日期方法
        dates = self.get_26_to_25_dates()

        # 返回带有日期范围的动作窗口
        return {
            'type': 'ir.actions.act_window',
            'name': '內部工單',
            'res_model': 'dtsc.makein',
            'view_mode': 'tree,form,kanban',
            'context': {
                'default_start_date': dates['default_start_date'],
                'default_end_date': dates['default_end_date'],
                'search_default_custom_26_to_25': 1,
            }
        } 
        
    @api.model
    def _get_delivery_date_domain(self):
        today = fields.Date.context_today(self)
        start_date = today.replace(day=26) + relativedelta(months=-1)
        end_date = today.replace(day=25) + relativedelta(months=1)
        return [('delivery_date', '>=', start_date), ('delivery_date', '<=', end_date)]
    
    @api.model
    def _get_delivery_date_range(self):
        today = datetime.today()

        # 计算起始日期：如果今天是月 26 日或之后，则起始日期是当月 26 日；否则是上月 26 日
        if today.day >= 26:
            start_date = today.replace(day=26)
            if today.month == 1:
                start_date = start_date.replace(month=12, year=today.year-1)
            else:
                start_date = start_date.replace(month=today.month-1)
        else:
            # 这里修正为上个月的 26 日
            if today.month == 1:
                start_date = today.replace(day=26, month=12, year=today.year-1)
            else:
                start_date = today.replace(day=26, month=today.month-1)

        # 计算结束日期：本月的 25 日
        end_date = today.replace(day=25)

        _logger.info('Start Date: %s, End Date: %s', start_date, end_date)
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    @api.model
    def action_window_make_in(self):
        # 调用日期范围计算
        start_date, end_date = self._get_delivery_date_range()
        _logger.info('action_window_make_in method triggered with start_date: %s and end_date: %s', start_date, end_date)
        filter_string = f"当前月度交货时间 ({start_date} 至 {end_date})"
        # 返回上下文中的动态日期
        return {
            'name': '內部工單',
            'type': 'ir.actions.act_window',
            'res_model': 'dtsc.makein',
            'view_mode': 'tree,form,kanban',
            'context': {
                'default_start_date': start_date,
                'default_end_date': end_date,
                'default_filter_string': filter_string, 
            },
        }
    ####权限
    
    is_in_by_sc = fields.Boolean(compute='_compute_is_in_by_sc')

    @api.depends("delivery_date")
    def _compute_delivery_date_show(self):
        for record in self:
           record.delivery_date_show = record.delivery_date 
        
        
    @api.depends()
    def _compute_is_in_by_sc(self):
        group_dtsc_sc = self.env.ref('dtsc.group_dtsc_sc', raise_if_not_found=False)
        user = self.env.user
        #_logger.info(f"Current user: {user.name}, ID: {user.id}")
        #is_in_group_dtsc_mg = group_dtsc_mg and user in group_dtsc_mg.users

        # 打印调试信息
        #_logger.info(f"User '{user.name}' is in DTSC MG: {is_in_group_dtsc_mg}, is in DTSC GLY: {is_in_group_dtsc_gly}")
        self.is_in_by_sc = group_dtsc_sc and user in group_dtsc_sc.users
    ####权限 

   
    
    def _inverse_delivery_date(self):
        for record in self:
            record.checkout_id.estimated_date = record.delivery_date
    
    
    @api.onchange("outmanall")
    def _onchange_outman(self):
        for record in self.order_ids:
            record.outman = self.outmanall.id
    
    
    @api.depends('order_ids.quantity','order_ids.total_size')
    def _compute_totals(self):
        for record in self:
            total_quantity = sum(line.quantity for line in record.order_ids)
            total_size = sum(line.total_size for line in record.order_ids)
            
            record.total_quantity = total_quantity
            record.total_size = total_size 
    
    def imageing_btn(self):
       self.write({"install_state":"imaged"})  
       
    # def imaged_btn(self):
       # self.write({"install_state":"imaged"}) 
       
    def making_btn(self): #开始制作生成口料单
       self.kld_btn()
       self.write({"install_state":"making"}) 
    
    def stock_in(self):
        install_name = self.name.replace("B","W")
        
        for record in self.order_ids:
            if not record.outman:
                raise UserError("請設置每一條輸出員工！")
                
        if not self.houzhiman:
            raise UserError("請錄入後置員工！")
        
        if not self.pinguanman:
            raise UserError("請錄入品管員工！")
        
        for record in self.order_ids:
            if record.product_id.make_ori_product_id.tracking == "serial":
                if record.is_stock_off == False:
                    raise UserError("請先去捲料扣料表完成扣料動作！")
        
        if self.no_mprlist == False:
            obj = self.env['dtsc.mpr'].search([('name', '=',install_name)],limit=1)
            if obj:
                if obj.state == "succ":
                    self.write({"install_state":"stock_in"})  
                else:
                    raise UserError("請先去扣料單完成扣料動作！")
            else:
                raise UserError("扣料單不存在請重新生成！")
        else:
            self.write({"install_state":"stock_in"})  
                
            
       
    def back_to(self):
        if self.install_state == 'making':
            self.write({"install_state":"imaged"})  
        elif self.install_state == 'imaged':
            self.write({"install_state":"draft"})
        elif self.install_state == 'stock_in':
            self.write({"install_state":"making"})  
            
                 
    
    def del_install_list(self):
        print("del_install_list")
        self.write({"install_state":"cancel"})        
        self.write({"name":self.name+"-D"})
    
    #生成扣料单
    def kld_btn(self):
        install_name = self.name.replace("B","W")
        is_install_id = self.env['dtsc.mpr'].search([('name', '=',install_name)],limit=1)
        if is_install_id:
            pass
        else:  
            product_values_dict = {}
            product_values_list = []
            product_product_obj = self.env['product.product']
            product_attribute_value_obj = self.env['product.attribute.value']
            
            for record in self.order_ids:
                if record.product_id.make_ori_product_id.tracking != "serial":
                    product_product_id = product_product_obj.search([('product_tmpl_id',"=",record.product_id.make_ori_product_id.id)],limit=1)
                   
                    key = record.product_id.id
                    if key in product_values_dict:
                        product_values_dict[key]['now_use'] += record.total_size
                    else:
                        product_values_dict[key] = {
                            'product_id':record.product_id.id,
                            'product_id_formake':record.product_id.make_ori_product_id.id,
                            'product_product_id':product_product_id.id,
                            'attr_name':"基础原料",
                            'uom_id':record.product_id.make_ori_product_id.uom_id.id,
                            'now_use': record.total_size,
                        }
                for attr_val in record.product_atts:
                    total_units_for_attr = record.total_size
                    if attr_val.make_ori_product_id.uom_id.name in ["件" , "個" , "支"]:
                        total_units_for_attr = record.quantity_peijian
                        
                    if attr_val.make_ori_product_id and attr_val.make_ori_product_id.tracking != "serial":
                        product_product_id = product_product_obj.search([('product_tmpl_id',"=",attr_val.make_ori_product_id.id)],limit=1)
                        key = product_product_id.id
                        if key in product_values_dict:
                            product_values_dict[key]['now_use'] += total_units_for_attr
                        else:
                            product_values_dict[key] = {
                                'product_product_id':product_product_id.id,
                                'product_id':record.product_id.id,
                                'product_id_formake':record.product_id.make_ori_product_id.id, 
                                'attr_name':attr_val.attribute_id.name+":"+attr_val.name,
                                'uom_id':attr_val.make_ori_product_id.uom_id.id,
                                'now_use':total_units_for_attr,
                            }
            product_values_list = [(0, 0, value) for value in product_values_dict.values()]
            
            if product_values_list:
                self.env['dtsc.mpr'].create({
                    'name' : install_name,             
                    'from_name' : install_name.replace("W","A"), 
                    'mprline_ids' : product_values_list,
                }) 
            else:
                self.no_mprlist = True
        
        
        
    

class MakeLine(models.Model):
    _name = 'dtsc.makeinline'
    sequence = fields.Char(string='項')
    make_order_id = fields.Many2one("dtsc.makein",ondelete='cascade')
    
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
    processing_method_after = fields.Text(string='後加工方式', compute='_compute_processing_method_after')
    output_material = fields.Char(string='輸出材質', compute='_compute_output_material')
    production_size = fields.Char(string='製作尺寸', compute='_compute_production_size')
    lengbiao = fields.Char(string='裱', compute='_compute_lengbiao')
    outman = fields.Many2one('dtsc.userlist',string="輸出" , domain=[('worktype_ids' , 'in' , [1])])
    is_modified = fields.Boolean(string="is modified",default = False)
    is_stock_off = fields.Boolean(default = False,compute="_compute_is_stock_off") 
    
   
        
    ####权限
    
    # is_in_by_sc = fields.Boolean(compute='_compute_is_in_by_sc')

    # @api.depends()
    # def _compute_is_in_by_sc(self):
        # group_dtsc_sc = self.env.ref('dtsc.group_dtsc_sc', raise_if_not_found=False)
        # user = self.env.user
        # #_logger.info(f"Current user: {user.name}, ID: {user.id}")
        # #is_in_group_dtsc_mg = group_dtsc_mg and user in group_dtsc_mg.users

        # # 打印调试信息
        # #_logger.info(f"User '{user.name}' is in DTSC MG: {is_in_group_dtsc_mg}, is in DTSC GLY: {is_in_group_dtsc_gly}")
        # self.is_in_by_sc = group_dtsc_sc and user in group_dtsc_sc.users
    ####权限
    barcode = fields.Char(
        string="條碼",
        compute='_compute_barcode',
        readonly=True,
        copy=False
    )
    
    barcode_image = fields.Binary(
        string="Barcode Image",
        compute='_generate_barcode_image'
    )
    
    @api.depends("barcode")
    def _compute_is_stock_off(self):
        for record in self:
            obj = self.env["dtsc.lotmprline"].search([('name', '=',record.barcode)],limit = 1)
            if obj:
                record.is_stock_off = True
            else:
                record.is_stock_off = False
            
        
        
        
        
    @api.depends('make_order_id.name', 'sequence')
    def _compute_barcode(self):
        for record in self:
            if record.make_order_id and record.sequence:
                record.barcode = f"{record.make_order_id.name}-{record.sequence}"
                # print("--------------------------") 
                # print(record.barcode) 
            else:
                record.barcode = False

    @api.depends('barcode')
    def _generate_barcode_image(self):
        for record in self:
            if record.barcode:
                barcode_type = barcode.get_barcode_class('code128')
                barcode_obj = barcode_type(record.barcode, writer=ImageWriter())

                buffer = BytesIO()
                barcode_obj.write(buffer, options={"write_text": False, "dpi": 300})

                # 这里我们不对图像大小做任何更改，保持其原始大小
                barcode_data = base64.b64encode(buffer.getvalue()).decode('utf-8')  # 使用buffer的内容

                record.barcode_image = barcode_data
                
                # print("==========================")
                # print(type(barcode_data))
                # print(barcode_data) 

                # 如果需要，将条形码保存为文件
                #with open('/tmp/barcode_{}.png'.format(record.id), 'wb') as f:
                #    f.write(base64.b64decode(barcode_data))

            
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
                    if att.attribute_id.name == "配件":
                        att_lines.append(f'{att.name}({round(record.quantity_peijian)})')
                    else:
                        att_lines.append(f'{att.name}')
            
            # if record.multi_chose_ids and record.multi_chose_ids != '[]':
                # att_lines.append(f'後加工：{record.multi_chose_ids}')
            
            # 合并属性行
            combined_value = '/'.join(att_lines)
            record.processing_method = combined_value
            
    @api.depends('multi_chose_ids', 'product_atts')
    def _compute_processing_method_after(self):
        for record in self:
            att_lines = []
                        
            if record.multi_chose_ids and record.multi_chose_ids != '[]':
                att_lines.append(f'後加工：{record.multi_chose_ids}')
            
            # 合并属性行
            combined_value = '/'.join(att_lines)
            record.processing_method_after = combined_value
            
    
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
            # attributes.extend(cold_laminated_values)
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
 

