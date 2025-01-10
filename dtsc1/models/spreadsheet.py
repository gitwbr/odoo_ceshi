from odoo import models, api

class CustomSpreadsheetDashboardGroup(models.Model):
    _inherit = 'spreadsheet.dashboard.group'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_spreadsheet_data(self):
        # 在这里，你可以添加你自己的逻辑来判断是否要阻止删除
        # 例如，你可以放宽或改变删除的条件
        pass  # 如果不做任何事，删除操作将不会被阻止
