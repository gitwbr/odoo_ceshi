from odoo import http
import json
from odoo.http import request

class Checkout(http.Controller):

    @http.route(['/checkout'], type='http', auth="public", website=True)
    def checkout(self, **kwargs):
        return http.request.render('dtsc.checkout_page', {})
    
    @http.route(['/order'], type='http', auth="public", website=True)
    def order(self, **kwargs):
        return http.request.render('dtsc.order_page', {})
    
    @http.route(['/hello', '/hello/<string:name>'], type='http', auth="public")
    #@http.route(['/hello'], type='http', auth="public", website=True)
    def hello(self, name="xxx", **kwargs):
        return "hello %s" %name
        
    @http.route('/habi', auth="public")
    def hello(self, **kwargs):
        return json.dumps({'a':1,'b':2})

    @http.route('/total', auth="public")
    def hello(self, **kwargs):               
        return "%s" %sum(request.env["sale.order"].search([]).mapped("amount_total"))
        
    # @http.route("/total/<string:date>")
    # def sale_total_at_date(self, date, **kw):
        # parsed_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        # sales = request.env['sale.order'].search([('date_order', '<=', parsed_date)])
        # return "%s" % sum(sales.mapped('amount_total'))