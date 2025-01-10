from odoo import models, fields, api
class ResPartner(models.Model):
    _inherit = "res.partner"
    
    is_company = fields.Boolean(string='Is a Company', default=True,
        help="Check if the contact is a company, otherwise it is a person")
    custom_init_name = fields.Char("簡稱")
    
    custom_id = fields.Char("編號")
    custom_fax = fields.Char("傳真")
    comment = fields.Char(string='廠區備注')
    comment_customer = fields.Char(string='客戶備注')  
    user_id = fields.Many2one(
        'res.users',
        compute='_compute_user_id', 
        precompute=True,  # avoid queries post-create
        readonly=False, store=True,
        help='The internal user in charge of this contact.')
    coin_can_cust = fields.Boolean(string="可下單客戶",default=False)
    # coin_can_cust1 = fields.Boolean(string="可下單客戶",default=False)
    sell_user = fields.Many2one("res.users" , string='銷售員' , domain=lambda self: [('groups_id', 'in', self.env.ref('dtsc.group_dtsc_yw').id)] )

    customclass_id = fields.Many2one("dtsc.customclass" , string='客戶分類')
    customclass_domain = fields.Many2many("dtsc.customclass" , compute='_compute_customclass_domain', store=False)
    custom_delivery_carrier = fields.Selection([
        ('freight', '貨運'),
        ('sale', '業務'),
        ('foreign', '外務'),
        ('post', '快遞'),
        ('self', '客戶自取'),
        ('diy', '自行施工'),
    ], string='交件方式')    
    custom_invoice_form = fields.Selection([
        ('21', '三聯式'),
        ('22', '二聯式'),
        ('other', '其他'),
    ], string='稅別')  
    
    custom_pay_mode = fields.Selection([
        ('1', '現金'),
        ('2', '支票'),
        ('3', '匯款'),
        ('4', '其他'),
    ], string='付款方式' ,default="1") 
     
    
    custom_contact_person = fields.Char("聯絡人")
    property_payment_term_id = fields.Many2one("account.payment.term" , string='客戶付款條款')
    vip_path = fields.Char("客戶資料夾")
    to_upload_file_required = fields.Boolean(string="必須上傳檔案",default=False)
   
    
    coin_can_supp = fields.Boolean(string="可下單供應商",default=False)
    supp_pay_mode = fields.Selection([
        ('1', '現金'),
        ('2', '支票'),
        ('3', '匯款'),
        ('4', '其他'),
    ], string='付款方式')    
    supp_pay_type = fields.Many2one("account.payment.term" , string='供應商付款條款')
    supp_invoice_addr = fields.Char("發票地址")
    purch_person = fields.Char("業務聯絡人")
    invoice_person = fields.Char("賬務聯絡人")    
    out_supp = fields.Boolean(string="外包供應商",default=False)
    supp_text = fields.Text(string="備注")
   
    is_customer = fields.Boolean("爲客戶" , compute="_compute_is_customer" , inverse="_set_is_customer")
    is_supplier = fields.Boolean("爲供應商",  compute="_compute_is_supplier", inverse="_set_is_supplier") 
     
     
    ####权限
    is_in_by_gly = fields.Boolean(compute='_compute_is_in_by_gly')
    
    
    @api.depends('sell_user')
    def _compute_customclass_domain(self):
        for record in self:
            if record.sell_user:
                # print(record.sell_user.id)
                record.customclass_domain = self.env['dtsc.customclass'].search([('sell_user', '=', record.sell_user.id)]).ids
                # print(record.customclass_domain)
            else:
                record.customclass_domain = []
                
    @api.depends()
    def _compute_is_in_by_gly(self):
        group_dtsc_gly = self.env.ref('dtsc.group_dtsc_gly', raise_if_not_found=False)
        user = self.env.user
        self.is_in_by_gly = group_dtsc_gly and user in group_dtsc_gly.users
     
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        # 检查当前用户是否是管理员
        if not (self.env.user.has_group('dtsc.group_dtsc_gly') or self.env.user.has_group('dtsc.group_dtsc_mg')):
            user_domain = [('sell_user', 'in', [self.env.user.id])]
            args = args + user_domain
        return super(ResPartner, self).search(args, offset, limit, order, count)
     
    @api.depends('customer_rank')
    def _compute_is_customer(self):
        for record in self:
            record.is_customer = record.customer_rank > 0
            
    @api.depends('supplier_rank')
    def _compute_is_supplier(self):
        for record in self:
            record.is_supplier = record.supplier_rank > 0
            
    def _set_is_customer(self):
        for record in self:
            record.customer_rank = 1 if record.is_customer else 0
            
    def _set_is_supplier(self):
        for record in self:
            record.supplier_rank = 1 if record.is_supplier else 0
            
    # _sql_constraints = [
        # ('name_unique', 'UNIQUE(name)', "不能設定相同的公司名")
    # ]  
    # _sql_constraints = [
        # ('name_uniq', 'CHECK(1=1)', 'Error: 名称必须唯一!')
    # ] 
    @api.model
    def create(self, vals):
        # 首先调用父类的create方法创建记录
        record = super(ResPartner, self).create(vals)

        # 检查是否已经提供了custom_id，如果没有，则生成它
        if not record.custom_id:
            prefix = 'S' if record.supplier_rank > 0 else 'C' if record.customer_rank > 0 else None
            if prefix:
                # 生成custom_id
                last_id = self.env['res.partner'].search([('custom_id', 'like', f'{prefix}%')], order='custom_id desc', limit=1).custom_id
                if last_id:
                    next_num = int(last_id[1:]) + 1
                else:
                    next_num = 1
                new_custom_id = f'{prefix}{next_num:04d}'

                # 更新记录的custom_id
                record.write({'custom_id': new_custom_id})

        return record