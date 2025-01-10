#!/usr/bin/python3
# @Time    : 2021-11-23
# @Author  : Kevin Kong (kfx2007@163.com)

from datetime import datetime, timedelta, date
from odoo.exceptions import AccessDenied, ValidationError
from odoo import models, fields, api
from odoo.fields import Command
import logging
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class Maketype(models.Model):

    _name = 'dtsc.maketype'
    _description = "後加工方式" 
    name = fields.Char('後加工名稱') 
    unit_char = fields.Char('單位描述')
    price = fields.Float('基礎價格')
