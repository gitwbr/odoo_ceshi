from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import logging

_logger = logging.getLogger(__name__)


class CustomWebsiteSale(WebsiteSale):
    
    @http.route(['/shop/address'], type='http', auth='public', website=True, sitemap=False)
    def address(self, **kw):
        # 调用父类的 address 方法，获得默认返回值
        result = super(CustomWebsiteSale, self).address(**kw)

        # 检查当前订单，设置默认国家为 ID 为 231
        order = request.website.sale_get_order()
        if not order.partner_id.country_id:
            order.partner_id.country_id = request.env['res.country'].browse(231)

        # 处理根据国家获取州列表的逻辑
        country = request.env['res.country'].browse(231)
        states = country.get_website_sale_states()

        # 更新渲染值，设置国家和州
        result.qcontext.update({
            'country': country,
            'country_states': states,
        })

        return result
        
        
    def _get_mandatory_fields_billing(self, country_id=False):
        req = ["name", "email", "street", "country_id"]
        if country_id:
            country = request.env['res.country'].browse(country_id)
            if country.state_required:
                req += ['state_id']
        return req

    def _get_mandatory_fields_shipping(self, country_id=False):
        req = ["name", "street", "country_id"]
        if country_id:
            country = request.env['res.country'].browse(country_id)
            if country.state_required:
                req += ['state_id']
        return req
    
    @http.route(['/shop/payment'], type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, **post):
        # 調用父類的 shop_payment 方法，獲取返回值
        result = super(CustomWebsiteSale, self).shop_payment(**post)

        # 獲取當前的銷售訂單
        order = request.website.sale_get_order()

        # 打印 order 及其地址信息
        if order:
            _logger.info(f"Order: {order}")
            billing_address = order.partner_id.contact_address
            shipping_address = order.partner_shipping_id.contact_address if order.partner_shipping_id else None
            _logger.info(f"Billing Address: {billing_address}")
            _logger.info(f"Shipping Address: {shipping_address}")

        # 返回原始 shop_payment 的結果
        return result