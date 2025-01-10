from odoo import models, fields

class CeshiModel(models.Model):
    _name = 'dtsc.ceshi'
    _description = '测试模型'

    name = fields.Char(string="名称")
