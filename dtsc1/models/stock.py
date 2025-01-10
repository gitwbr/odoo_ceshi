from datetime import datetime, timedelta, date
from odoo.exceptions import AccessDenied, ValidationError
from odoo import models, fields, api
from odoo.fields import Command
from odoo import _
import logging
import math
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import math
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = "stock.quant"
    
    lastmodifydate = fields.Datetime("最後修改時間",compute="_compute_lastmodifydate")
    zksl_cai = fields.Float("在庫數量(才)",compute="_compute_zksl_cai")
    
    @api.depends('quantity')
    def _compute_zksl_cai(self):
        for record in self:
            if record.lot_id:
                uom_obj = self.env["uom.uom"]
                uom_record = uom_obj.browse(record.product_uom_id.id)
                now_category_id = uom_record.category_id.id
                other_uom = uom_obj.search([( 'category_id' , "=" , now_category_id ) , ("id","!=",uom_record.id)],limit=1)
                record.zksl_cai = round(record.quantity * other_uom.factor,1)
            else:
                record.zksl_cai = 0    
    
    def _domain_product_id(self):
        if not self._is_inventory_mode():
            return
        domain = [('type', '=', 'product'), ('product_tmpl_id.purchase_ok', '=', True)]
        if self.env.context.get('product_tmpl_ids') or self.env.context.get('product_tmpl_id'):
            products = self.env.context.get('product_tmpl_ids', []) + [self.env.context.get('product_tmpl_id', 0)]
            domain = expression.AND([domain, [('product_tmpl_id', 'in', products)]])
        return domain
    
    @api.depends('quantity', 'product_id.stock_move_ids', 'lot_id')
    def _compute_lastmodifydate(self):
        for record in self:
            domain = [('product_id', '=', record.product_id.id)]
            if record.lot_id:
                domain.append(('lot_id', '=', record.lot_id.id))

            move_lines = self.env['stock.move.line'].search(
                domain, order='date desc', limit=1)
            if move_lines:
                record.lastmodifydate = move_lines.date
            else:
                record.lastmodifydate = None
    

class Productproduct(models.Model):
    _inherit = "product.product"
    
    sec_uom_id = fields.Many2one("uom.uom")
    
class StockMove(models.Model):
    _inherit = "stock.move"
    
    reference = fields.Char(compute='_compute_reference_new', string="Reference", store=True)
    
    @api.depends('picking_id', 'name')
    def _compute_reference_new(self):
        for move in self:
            if move.reference:
                move.reference = move.reference
            else:
                move.reference = move.picking_id.name if move.picking_id else move.name
        
        
class Mpr(models.Model):
    _name = "dtsc.mpr"
    _order = "name desc"
    name = fields.Char("單號")
    from_name = fields.Char("銷售單號")
    state = fields.Selection([
        ("draft","待扣料"),
        ("succ","扣料完成"),   
    ],default='draft' ,string="狀態")
    mprline_ids = fields.One2many("dtsc.mprline" , "mpr_id")
    picking_id = fields.Many2one("stock.picking")
    stock_move_id = fields.Many2one("stock.move")
    stock_move_line_id = fields.Many2many("stock.move.line")
    stock_location_id = fields.Many2one("stock.location", string="倉庫",domain=[('usage', '=', 'internal')] ,default = 8 )
     
    def back_btn(self):
        self.ensure_one()
        if not self.picking_id or self.picking_id.state != 'done':
            raise UserError('无有效的完成拣货操作，无法回退。')

        # 创建逆向拣货记录
        reverse_picking_vals = {
            'picking_type_id': self.picking_id.picking_type_id.id,
            'location_id': self.picking_id.location_dest_id.id,
            'location_dest_id': self.picking_id.location_id.id,
            'origin': '退回 ' + self.name.replace("W","B"),
        }
        reverse_picking = self.env['stock.picking'].create(reverse_picking_vals)
        
        
        for move in self.picking_id.move_ids:
        
            reverse_move_vals = {
                'name': move.name,
                'reference': "退回" + self.name.replace("W","B"),
                'origin' : self.name.replace("W","B"),
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty,
                'quantity_done': move.quantity_done,
                'product_uom': move.product_uom.id,
                'picking_id': reverse_picking.id,
                'location_id': move.location_dest_id.id,
                'location_dest_id': move.location_id.id,
            }
            reverse_move = self.env['stock.move'].create(reverse_move_vals)
            # print(line.id)  
            # 处理序列号
            for move_line in move.move_line_ids:
                print("========================")
                if move_line.lot_id:
                    # print(move_line.product_id.name)
                    # print(move_line.lot_id.name)
                    # print(move_line.lot_id.id)
                    reverse_move_line_vals = {
                        'reference' : "退回"+self.name.replace("W","B"), 
                        'origin' : self.name.replace("W","B"),
                        'move_id': reverse_move.id,
                        'product_id': move_line.product_id.id,
                        'product_uom_id': move_line.product_uom_id.id,
                        'picking_id': reverse_picking.id,
                        'reserved_uom_qty': move_line.qty_done,
                        'qty_done': move_line.qty_done,
                        'lot_id': move_line.lot_id.id,  # 指定序列号
                        'location_id': move_line.location_dest_id.id,
                        'location_dest_id': move_line.location_id.id,
                    }
                    moveline  = self.env['stock.move.line'].create(reverse_move_line_vals)
                    move_line_objs = self.env['stock.move.line'].search([("product_id" , "=" ,move_line.product_id.id ),("lot_id" ,"=" , False ),('picking_id',"=", reverse_picking.id)])
                    move_line_objs.unlink()
            
        # for line in reverse_move.move_line_ids:
             # print(line.id)    
        # 确认并完成逆向拣货
        reverse_picking.action_confirm()
        reverse_picking.action_assign()
        reverse_picking.button_validate()
        
        
        self.write({'state': 'draft'})
    
    def floor_to_one_decimal_place(self,number):
        return math.floor(number * 10) / 10
        
        
    def confirm_btn(self):
        for record in self.mprline_ids:
            if record.product_product_id.product_tmpl_id.tracking == "serial": #如果這個產品設定的是有唯一序列號的 則需要選擇序號
                if not record.product_lot:
                    raise UserError('%s 還未選擇正確的序號！' %record.product_product_id.name)
                  
            if record.final_use < 0:
                raise UserError('%s 扣料必須大於0！' %record.product_product_id.name)
            elif record.final_use == 0:
                record.final_use = record.now_use
        
        now_stock_location_id = self.stock_location_id.id   
        
        picking = self.env['stock.picking'].create({
            # 'name':self.name.replace("W","B/W/"),
            'picking_type_id' : 1,
            'location_id': now_stock_location_id,  #库存
            'location_dest_id': 15, #Production 用于生产
            'origin' : self.name.replace("W","B"), 
        })
        
        self.write({'picking_id': picking.id})
        uom_obj = self.env["uom.uom"]
        
        for record in self.mprline_ids:
            uomid = record.uom_id.id
            
            if "卷" in record.uom_id.name:
                uom_record = uom_obj.browse(record.uom_id.id)
                now_category_id = uom_record.category_id.id
                other_uom = uom_obj.search([( 'category_id' , "=" , now_category_id ) , ("id","!=",uom_record.id)],limit=1)
                uomid = other_uom.id
            
            final_use = record.final_use
            if record.product_lot: 
                quant = self.env["stock.quant"].search([('product_id' , "=" , record.product_product_id.id),("lot_id" ,"=" , record.product_lot.id),("location_id" ,"=" ,now_stock_location_id)],limit=1) #這裡出現的負數我用company_id隱藏，未來要修正
                if quant:
                    uom_record = uom_obj.browse(record.uom_id.id)
                    now_category_id = uom_record.category_id.id
                    other_uom = uom_obj.search([( 'category_id' , "=" , now_category_id ) , ("id","!=",uom_record.id)],limit=1)
                    if other_uom.name == "才":
                        if quant.quantity * other_uom.factor < record.final_use:
                            raise UserError('%s 實際扣料大於庫存！' %record.product_product_id.name)
                            # final_use = round(quant.quantity * other_uom.factor,3)
                            final_use = self.floor_to_one_decimal_place(quant.quantity * other_uom.factor)
                    
                    
                    #如果勾选扣除余料，则按照卷的单位来扣 更精准
                    if record.is_all == True:
                        uomid = record.uom_id.id
                        final_use = quant.quantity
            
            move = self.env['stock.move'].create({
                'name' : self.name.replace("W","B/W/"),
                'reference' : "工单扣料"+self.name.replace("W","B"), 
                'product_id': record.product_product_id.id,
                'product_uom_qty' : final_use,
                'product_uom' : uomid,
                "picking_id" : picking.id,
                "quantity_done" : final_use,
                'origin' : self.name.replace("W","B"),
                'location_id': now_stock_location_id,  #库存
                'location_dest_id': 15, #Production 用于生产                
            })
            self.write({'stock_move_id': move.id})
            
            if record.product_lot:    
                # move_line_obj = self.env['stock.move.line'].browse(move.id)
                move_line = self.env['stock.move.line'].create({
                    'reference' : "工单扣料"+self.name.replace("W","B"), 
                    'origin' : self.name.replace("W","B"),
                    "move_id": move.id, 
                    "picking_id" : picking.id,
                    'product_id': record.product_product_id.id,
                    'qty_done': final_use ,
                    'product_uom_id' : uomid,                
                    'location_id': now_stock_location_id,  #库存
                    'location_dest_id': 15, #Production 用于生产 
                    'lot_name' : record.product_lot.name,
                    'lot_id': record.product_lot.id,
                    'state': "draft",
                })                
                self.stock_move_line_id = [(4, move_line.id)]
                move_line_objs = self.env['stock.move.line'].search(["|",("lot_id" ,"=" , False ),("lot_name" ,"=" , False ),("product_id" , "=" ,record.product_product_id.id ),('picking_id',"=", picking.id)])
                move_line_objs.unlink()
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate() 
        
        self.write({"state":"succ"})
    
class MprLine(models.Model):
    _name = "dtsc.mprline"
    
    mpr_id = fields.Many2one("dtsc.mpr")
    # final_use_readonly = fields.Boolean(compute='_compute_final_use_readonly', default=False, store=False)
    purchase_product_id = fields.Many2one("dtsc.checkout",readonly=True)
    product_product_id = fields.Many2one("product.product" , "物料名稱")
    product_lot = fields.Many2one("stock.lot" , "產品序號")
    product_id_formake=fields.Many2one('product.template',readonly=True) 
    product_id = fields.Many2one("product.template" , "製作物" ,readonly = True)
    attr_name = fields.Char("屬性名",readonly=True)
    uom_id = fields.Many2one('uom.uom',string="單位")
    now_use = fields.Float("预计消耗" ,readonly=True)
    final_use = fields.Float("实际消耗")
    lot_stock_num = fields.Char(string = "單序號庫存" ,compute = '_compute_lot_stock_num')
    now_stock = fields.Char(string='總庫存',compute = '_compute_now_stock' ,readonly=True)
    barcode_input = fields.Char("條碼輸入")
    comment = fields.Char("備註")
    is_all = fields.Boolean("扣除餘料")
    
    ####权限
    is_in_by_mg = fields.Boolean(compute='_compute_is_in_by_mg')
    
    def floor_to_one_decimal_place(self,number):
        return math.floor(number * 10) / 10
    
    @api.onchange("is_all","mpr_id.now_stock_location_id")
    def change_is_all(self): 
        uom_obj = self.env["uom.uom"]    
        for record in self:
            if self.is_all == True:
                if record.product_lot.id:
                
                    quant = self.env["stock.quant"].search([('product_id' , "=" , record.product_product_id.id),("lot_id" ,"=" , record.product_lot.id),("location_id" ,"=" ,8)],limit=1) #這裡出現的負數我用company_id隱藏，未來要修正
                
                    if quant:
                        uom_record = uom_obj.browse(record.uom_id.id)
                        now_category_id = uom_record.category_id.id
                        other_uom = uom_obj.search([( 'category_id' , "=" , now_category_id ) , ("id","!=",uom_record.id)],limit=1)
                        if other_uom.name == "才":
                            record.final_use = self.floor_to_one_decimal_place(quant.quantity * other_uom.factor)
                        else:
                            record.final_use = quant.quantity
                    else:
                        raise UserError('該序號產品沒有庫存。')
                else:
                    raise UserError('非序號產品無法扣除餘料。')
    
    @api.depends("product_product_id")
    def _compute_is_in_by_mg(self):
        group_dtsc_mg = self.env.ref('dtsc.group_dtsc_mg', raise_if_not_found=False)
        user = self.env.user
        #_logger.info(f"Current user: {user.name}, ID: {user.id}")
        #is_in_group_dtsc_mg = group_dtsc_mg and user in group_dtsc_mg.users

        # 打印调试信息
        #_logger.info(f"User '{user.name}' is in DTSC MG: {is_in_group_dtsc_mg}, is in DTSC GLY: {is_in_group_dtsc_gly}")
        self.is_in_by_mg = group_dtsc_mg and user in group_dtsc_mg.users
        
    is_in_by_sc = fields.Boolean(compute='_compute_is_in_by_sc')

    @api.depends("product_product_id")
    def _compute_is_in_by_sc(self):
        group_dtsc_sc = self.env.ref('dtsc.group_dtsc_sc', raise_if_not_found=False)
        user = self.env.user
        #_logger.info(f"Current user: {user.name}, ID: {user.id}")
        #is_in_group_dtsc_mg = group_dtsc_mg and user in group_dtsc_mg.users

        # 打印调试信息
        #_logger.info(f"User '{user.name}' is in DTSC MG: {is_in_group_dtsc_mg}, is in DTSC GLY: {is_in_group_dtsc_gly}")
        self.is_in_by_sc = group_dtsc_sc and user in group_dtsc_sc.users
        
    is_in_by_ck = fields.Boolean(compute='_compute_is_in_by_ck')

    @api.depends("product_product_id")
    def _compute_is_in_by_ck(self):
        group_dtsc_ck = self.env.ref('dtsc.group_dtsc_ck', raise_if_not_found=False)
        user = self.env.user
        #_logger.info(f"Current user: {user.name}, ID: {user.id}")
        #is_in_group_dtsc_mg = group_dtsc_mg and user in group_dtsc_mg.users

        # 打印调试信息
        #_logger.info(f"User '{user.name}' is in DTSC MG: {is_in_group_dtsc_mg}, is in DTSC GLY: {is_in_group_dtsc_gly}")
        self.is_in_by_ck = group_dtsc_ck and user in group_dtsc_ck.users
    ####权限
    
    @api.model
    def create(self, vals):
        mpr_record = self.env['dtsc.mpr'].browse(vals.get('mpr_id'))
        if mpr_record.state == 'succ':
            raise UserError('不允許在此狀態下添加記錄。')
        return super(MprLine, self).create(vals)

    def write(self, vals):
        if self.mpr_id.state == 'succ':
            raise UserError('不允許在此狀態下修改記錄。')
        return super(MprLine, self).write(vals)

    def unlink(self):
        if any(line.mpr_id.state == 'succ' for line in self):
            raise UserError('不允許在此狀態下刪除記錄。')
        return super(MprLine, self).unlink()

    @api.onchange('barcode_input')
    def _onchange_barcode_input(self):
        if self.barcode_input:
            parts = self.barcode_input.split('-')
            if len(parts) > 2:
                # 假设 a 是 product_product_id 的外部 ID
                product = self.env['product.product'].search([('default_code', '=', parts[0])])
                if product:
                    self.product_product_id = product.id
                # 假设 b 是 product_lot 的名称
                # lot = self.env['stock.lot'].search([('name', '=', parts[1]+"-"+parts[2])])
                lot = self.env['stock.lot'].search([('barcode', '=', self.barcode_input)])
                if lot:
                    self.product_lot = lot.id

    
    @api.onchange("product_product_id")
    def change_uom(self):
        for record in self:
            if self.product_product_id:
                self.uom_id = self.product_product_id.uom_id.id
    
    
    @api.depends('product_id','product_product_id',"product_lot")
    def _compute_lot_stock_num(self):
        uom_obj = self.env["uom.uom"]
        for record in self:
            if record.product_lot.id:
            
                quant = self.env["stock.quant"].search([('product_id' , "=" , record.product_product_id.id),("lot_id" ,"=" , record.product_lot.id),("location_id" ,"=" ,8)],limit=1) #這裡出現的負數我用company_id隱藏，未來要修正
            
                if quant:
                    uom_record = uom_obj.browse(record.uom_id.id)
                    now_category_id = uom_record.category_id.id
                    other_uom = uom_obj.search([( 'category_id' , "=" , now_category_id ) , ("id","!=",uom_record.id)],limit=1)
                    if other_uom.name == "才":
                        # record.lot_stock_num = str(round(quant.quantity,1)) + "(" + str(round(quant.quantity * other_uom.factor,1)) +" 才)"
                        record.lot_stock_num = str(round(quant.quantity,3)) + "(" + str(self.floor_to_one_decimal_place(quant.quantity * other_uom.factor)) +" 才)"
                    else:
                        record.lot_stock_num = quant.quantity
                else:
                    record.lot_stock_num = "無"
            else:
                record.lot_stock_num = "無"
    
    @api.depends('product_id','product_product_id','mpr_id.stock_location_id')
    def _compute_now_stock(self):
        for record in self:
            print(record.mpr_id.stock_location_id.id)
            print(record.product_product_id.id)
            quant = self.env["stock.quant"].search([('product_id' , "=" , record.product_product_id.id),("location_id" ,"=" ,record.mpr_id.stock_location_id.id)],limit=1) #這裡出現的負數我用company_id隱藏，未來要修正
            if quant:
                record.now_stock = quant.quantity
            else:
                record.now_stock = "0"
         

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    description = fields.Text(string="採購描述" , related="move_id.purchase_line_id.name")
    
    
    # remark = fields.Text(string="備註")
    # def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
 
        # self.ensure_one()
        # if self.remark:
            # if fields.Float.is_zero(qty, 0, precision_rounding=self.product_uom_id.rounding):
                # name = "數量確認 (" + self.remark+")"
            # else:
                # name = "數量更新 (" + self.remark +")"
        
        # self.write({"remark":""})
        # return {
            # 'name': self.env.context.get('inventory_name') or name,
            # 'product_id': self.product_id.id,
            # 'product_uom': self.product_uom_id.id,
            # 'product_uom_qty': qty,
            # 'company_id': self.company_id.id or self.env.company.id,
            # 'state': 'confirmed',
            # 'location_id': location_id.id,
            # 'location_dest_id': location_dest_id.id,
            # 'is_inventory': True,
            # 'move_line_ids': [(0, 0, {
                # 'product_id': self.product_id.id,
                # 'product_uom_id': self.product_uom_id.id,
                # 'qty_done': qty,
                # 'location_id': location_id.id,
                # 'location_dest_id': location_dest_id.id,
                # 'company_id': self.company_id.id or self.env.company.id,
                # 'lot_id': self.lot_id.id,
                # 'package_id': out and self.package_id.id or False,
                # 'result_package_id': (not out) and self.package_id.id or False,
                # 'owner_id': self.owner_id.id,
            # })]
        # }

class ReportStockQuant(models.AbstractModel):
    _name = 'report.dtsc.report_inventory'
    
    
    @api.model
    def _get_report_values(self, docids, data=None):
        # 获取所有特定位置的stock.quant
        quants = self.env['stock.quant'].search([('location_id', '=', 8)])
        product_quant_map = {}

        for quant in quants:
            # 对每个quant, 找到对应的stock.move.line和stock.move
            move_lines = self.env['stock.move.line'].search([
                ('lot_id', '=', quant.lot_id.id),
                ('location_id', '=', 4)
            ], limit=1)

            if move_lines:
                move = move_lines.move_id
                if move:
                    # 对于每个产品，累计其数量和总价格
                    if quant.product_id not in product_quant_map:
                        #product_quant_map[quant.product_id] = {'total_price': 0.0, 'total_qty': 0.0}
                        product_quant_map[quant.product_id] = {
                            'total_qty': 0.0,
                            'uom': quant.product_uom_id.name  
                        }
                    
                    product_quant_map[quant.product_id]['total_qty'] += quant.quantity
        
       
        
        # 准备传递给报告的数据
        report_data = []
        for product, data in product_quant_map.items():
            report_data.append({
                'product_id': product,
                'quantity': data['total_qty'],
                'uom': data['uom']
            })

        return {
            'doc_ids': docids,
            'doc_model': 'stock.quant',
            'data': report_data,  # 传递合并后的数据给报告
        }

    
        
class ReportStockQuantAmount(models.AbstractModel):
    _name = 'report.dtsc.report_inventory_amount'
    
    
    # @api.model
    # def _get_report_values(self, docids, data=None):
        # quants = self.env['stock.quant'].search([('location_id', '=', 8)])
        # for quant in quants:
            # # 根据lot_id和location_id找到对应的stock.move.line
            # move_lines = self.env['stock.move.line'].search([
                # ('lot_id', '=', quant.lot_id.id),
                # ('location_id', '=', 4)  # 根据您的描述，这里使用location_id=4
            # ], limit=1)  # 假设我们只关心找到的第一条记录
            
            # if move_lines:
                # move = move_lines.move_id  # 从stock.move.line获取stock.move
                # if move:
                    # # 现在我们有了move对象，可以获取price_unit
                    # quant.purchase_price = move.price_unit
                # else:
                    # quant.purchase_price = 0
            # else:
                # quant.purchase_price = 0
        
        # return {
            # 'doc_ids': docids,
            # 'doc_model': 'stock.quant',
            # 'docs': quants,
            # 'data': data,
        # }
    @api.model
    def _get_report_values(self, docids, data=None):
        # 获取所有特定库位的 stock.quant 记录
        quants = self.env['stock.quant'].search([('location_id', '=', 8)])  # 可以修改搜索条件以匹配所有库位
        product_quant_map = {}

        for quant in quants:
            product = quant.product_id

            # 获取该产品在采购订单中的采购记录
            purchase_lines = self.env['purchase.order.line'].search([('product_id', '=', product.id)])
            
            total_purchase_qty = 0.0
            total_purchase_price = 0.0

            # 计算该产品的采购总数量和总金额
            for purchase_line in purchase_lines:
                total_purchase_qty += purchase_line.product_qty
                total_purchase_price += purchase_line.price_unit * purchase_line.product_qty

            # 计算该产品在采购订单中的平均价格
            avg_purchase_price = round(total_purchase_price / total_purchase_qty, 1) if total_purchase_qty > 0 else 0.0

            # 初始化该产品在 product_quant_map 中的条目
            if product not in product_quant_map:
                product_quant_map[product] = {
                    'total_price': 0.0,
                    'total_qty': 0.0,
                    'average_price': 0.0,  # 添加平均价格字段
                    'uom': quant.product_uom_id.name  
                }

            # 更新库存中的总数量
            product_quant_map[product]['total_qty'] += quant.quantity

            # 将计算的平均采购价格存入 product_quant_map
            product_quant_map[product]['average_price'] = avg_purchase_price

            # 更新总价，按照从采购订单中的平均进价乘以库存数量
            product_quant_map[product]['total_price'] = avg_purchase_price * product_quant_map[product]['total_qty']

            # 打印调试信息，确保正确获取产品的采购价格和库存信息
            if product.display_name == "鐵腳架-180cm-直":
                print(f"鐵腳架-180cm-直: Average Purchase Price = {avg_purchase_price}, "
                      f"Total Stock Quantity = {product_quant_map[product]['total_qty']}, "
                      f"Total Price = {product_quant_map[product]['total_price']}")

        # 准备传递给报告的数据
        report_data = []
        for product, data in product_quant_map.items():
            # 将数据传递到模板
            report_data.append({
                'product_id': product,
                'quantity': data['total_qty'],  # 库存中的总数量
                'average_price': data['average_price'],  # 从采购订单中计算的平均进价
                'total_price': data['total_price'],  # 按照进价乘以库存数量
                'uom': data['uom']
            })

            # 打印调试信息
            print(f"Appending data for report: {product.display_name}, Quantity: {data['total_qty']}, "
                  f"Average Price: {data['average_price']}, Total Price: {data['total_price']}")

        return {
            'doc_ids': docids,
            'doc_model': 'stock.quant',
            'data': report_data,  # 传递合并后的数据给报告
        }


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    purchase_price = fields.Float('採購價格')
        
class ReportStockQuantBase(models.AbstractModel):
    _name = 'report.dtsc.report_inventory_base'
    
    
    @api.model
    def _get_report_values(self, docids, data=None):
        quants = self.env['stock.quant'].search([('location_id', '=', 8)])
        for quant in quants:
            # 根据lot_id和location_id找到对应的stock.move.line
            move_lines = self.env['stock.move.line'].search([
                ('lot_id', '=', quant.lot_id.id),
                ('location_id', '=', 4)  # 根据您的描述，这里使用location_id=4
            ], limit=1)  # 假设我们只关心找到的第一条记录
            
            if move_lines:
                move = move_lines.move_id  # 从stock.move.line获取stock.move
                if move:
                    # 现在我们有了move对象，可以获取price_unit
                    quant.purchase_price = move.price_unit
                else:
                    quant.purchase_price = 0
            else:
                quant.purchase_price = 0
        
        return {
            'doc_ids': docids,
            'doc_model': 'stock.quant',
            'docs': quants,
            'data': data,
        }           