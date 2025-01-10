from odoo import models, fields, api
import math
import base64
import requests
import json
import os.path
import datetime
import pytz
from datetime import datetime, timedelta, date
from urllib.parse import quote_plus
from odoo.exceptions import UserError

class Imagelist(models.Model):
    _name = 'dtsc.imagelist'

    install_id = fields.Many2one("dtsc.installproduct")
    image = fields.Binary(string="Image")

class Installproduct(models.Model):
    _name = 'dtsc.installproduct'
    
    name = fields.Char(string='單號')
    install_state = fields.Selection([
        ("draft","草稿"),
        ("installing","施工中"),
        ("succ","完成"),
        ("cancel","作廢"),    
    ],default='draft' ,string="狀態")
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    xcllr = fields.Char("現場聯絡人") 
    xcllr_phone = fields.Char("聯絡人電話")
    
    cbsllr = fields.Char("承包商聯絡人")
    cbsllr_phone = fields.Char("承包商電話")
    
    in_date = fields.Datetime(string='進場時間')
    out_date = fields.Datetime(string='撤場時間')
    
    address = fields.Char(string='施工地址') 
    comment = fields.Char(string="備註")
    google_comment = fields.Char(string="行事曆備註")
    
    zcs = fields.Float(string="總才數", compute='_compute_totals')
    fzyw = fields.Char(string="負責業務")
    
    total_quantity = fields.Integer(string='本單總數量', compute='_compute_total_quantity')
    # total_size = fields.Integer(string='本單總才數', compute='_compute_totals')
    image = fields.Binary(string="Image")
    # image_urls = fields.Text(string="Image URL" ,default='[]')
    # images_html = fields.Text(readonly=True,compute="_compute_images_html")
    image_ids = fields.One2many('dtsc.imagelist', 'install_id', string='Images') 
    email_id = fields.Many2one('res.partner', string='施工方' ,domain=[('supplier_rank',">",0)] )
    signature = fields.Binary(string='簽名')
     

    # def scan_qr_button(self):
        # pass
    # def close_qr_button(self):
        # pass
     
    # def process_qr_code(self, qr_code):
        # if not qr_code:
            # raise ValueError("二维码数据不能为空")  # 检查二维码数据
        # else:
            # print(f"处理的二维码数据: {qr_code}")
        # return {"status": "success"}  # 返回成功的响应
        
        
    
    @api.depends("image_urls")
    def _compute_images_html(self): 
        
        for record in self: 
            urls = json.loads(record.image_urls)
            imgs = ''.join([
                f'<div style="display:inline-block;">'
                f'<img src=https://localhost/uploads_makein/{url} width="150" height="auto"/>'
                # f'<button type="button" onclick="odoo.define(\'dtsc.makein\',function(require){{'
                # f'var rpc=require(\'web.rpc\')'
                # f'rpc.query({{'
                # f'model:\'dtsc.makein\','
                # f'method:\'delete_image\','
                # f'args:[{record.id},\'{url}\'],'
                # f'}}).then(function(){{'
                # f'location.reload();'
                # f'}})'
                # f'}})">Delete</button>'
                f'<button type="button" onclick="deleteImage(\'dtsc.installproduct\',{record.id},\'{url}\')">delete</button>'
                f'</div>'
                for url in urls])
            
            record.images_html = imgs
    
    def delete_image(self,image_url):
        self.ensure_one()
        urls = json.loads(self.image_urls)
        if image_url in urls:
            urls.remove(image_url)
        self.image_urls = json.dumps(urls)
        
    @api.depends('install_product_ids.shuliang') 
    def _compute_total_quantity(self):
        total = 0
        for record in self:
            for line in record.install_product_ids:
                total += line.shuliang
            
        record.total_quantity = total 
    
    @api.depends('install_product_ids.caishu')
    def _compute_totals(self):
        total = 0
        for record in self:
            for line in record.install_product_ids:
                total += line.caishu #* line.shuliang
            
        record.zcs = total 
    
    def send_google(self):
        # mail_template = self.env.ref('my_module.my_mail_template_id')
        # 如果没有使用模板，也可以直接创建邮件
        if not self.address:
            raise UserError('請輸入施工地址。')
            
        if not self.in_date:
            raise UserError('請輸入開始時間。')
            
        if not self.out_date:
            raise UserError('請輸入結束時間。')
            
        if not self.email_id:
            raise UserError('請選擇施工法後才能發送谷歌行事曆。')
        
        if not self.email_id.email:
            raise UserError('請填寫施工方郵箱後才能發送谷歌行事曆。')
        
        action = "施工日曆提醒"
        details = ""
        if self.xcllr:
            details += "現場聯絡人：" + self.xcllr + "\n"
        if self.xcllr_phone:
            details += "現場聯絡人電話：" + self.xcllr_phone + "\n"
        if self.google_comment:
            details += "備註：" + self.google_comment + "\n"
        if self.address:
            details += "地址：" + self.address + "\n"
             
            
            
        mailstring = "<p>科影提示您有一項施工需要注意，點擊下方鏈接加入行事曆！</p>"
        
        in_date = self.in_date
        out_date = self.out_date 
        
        location = self.address
        text = "施工日曆提醒"
        
        tz = pytz.timezone('Asia/Shanghai')  # UTC+8
        in_date_utc = in_date.astimezone(pytz.utc)
        out_date_utc = out_date.astimezone(pytz.utc)
        # 格式化日期时间为Google日历所需的格式
        start_date_str = in_date_utc.strftime('%Y%m%dT%H%M%SZ')
        end_date_str = out_date_utc.strftime('%Y%m%dT%H%M%SZ')
        
        in_date_utc1 = in_date.astimezone(tz)
        out_date_utc1 = out_date.astimezone(tz)
        
        start_date_str1 = in_date_utc1.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str1 = out_date_utc1.strftime('%Y-%m-%d %H:%M:%S')
        
        details += "進場時間：" + start_date_str1 + "\n" 
        details += "撤場時間：" + end_date_str1 + "\n"
        # URL编码详情和地点
        details_encoded = quote_plus(details)
        location_encoded = quote_plus(location)
        # 构建URL
        url_template = "https://calendar.google.com/calendar/r/eventedit?action=TEMPLATE&dates={start}/{end}&details={details}&location={location}&text={text}"
        url_filled = url_template.format(
            start=start_date_str,
            end=end_date_str,
            details=details_encoded,
            location=location_encoded,
            text=quote_plus(text)
        )
        # url = https://calendar.google.com/calendar/r/eventedit?action=TEMPLATE&dates=20230325T224500Z%2F20230326T001500Z&stz=Europe/Brussels&etz=Europe/Brussels&details=EVENT_DESCRIPTION_HERE&location=EVENT_LOCATION_HERE&text=EVENT_TITLE_HERE

      
        mailstring += f'<p><a href="{url_filled}">加入行事曆</a></p>'
        
        
        print(self.email_id.email)
        
        mail_values = {
            'email_from': self.env.user.email_formatted,
            'email_to': self.email_id.email,
            'subject': '科影施工提示',
            'body_html': '<p>'+mailstring+'</p>',
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
        #https://calendar.google.com/calendar/r/eventedit?action=TEMPLATE&dates=20230325T224500Z%2F20230326T001500Z&stz=Europe/Brussels&etz=Europe/Brussels&details=EVENT_DESCRIPTION_HERE&location=EVENT_LOCATION_HERE&text=EVENT_TITLE_HERE

    
    
    
        '''
        return
        SERVICE_ACCOUNT_FILE = '/home/ubuntu/odooC/config/credentials.json'

        # 定义所需的API范围
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # 使用服务账户认证并创建API客户端
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)

        # 创建日历事件
        event = {
            'summary': '会议主题',
            'location': '会议地点',
            'description': '会议描述',
            'start': {
                'dateTime': '2024-03-05T09:00:00-07:00',
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': '2024-03-05T10:00:00-07:00',
                'timeZone': 'America/Los_Angeles',
            },
            'attendees': [
                {'email': 'bryant@habilisnet.com'},
                {'email': 'attendee2@example.com'},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
 
        # 添加事件到日历
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event_result.get('htmlLink')}")
        '''
    def send_install_list(self):
        self.write({"install_state":"installing"})        
        print("send_install_list")
        
    def succ_install_list(self):
        self.write({"install_state":"succ"})        
        print("send_install_list")
        
    def back_install_list(self):
        if self.install_state == "succ":
            self.write({"install_state":"installing"})  
        elif self.install_state == "installing":
            self.write({"install_state":"draft"})  
        print("send_install_list")
        
    def del_install_list(self):
        print("del_install_list")
        self.write({"install_state":"cancel"})        
        self.write({"name":self.name+"-D"})
    
    def upload_image(self):
        if self.image:
            self.env['dtsc.imagelist'].create({
                'image': self.image,
                'install_id': self.id,
            })
            self.image = False
        return True
        # for record in self:
            # if record.image:
                # url = 'http://127.0.0.1/upload_makein.php'
                # image_data = base64.b64decode(record.image)
                # files = {'file' : (self.name ,image_data ,'image/jpeg')}
                # response = requests.post(url,files=files)
                
                # if response.status_code == 200:
                    # current_urls = json.loads(record.image_urls)
                    # current_urls.append(response.text)
                    
                    
                    # record.image_urls = json.dumps(current_urls)#response.text
                    # record.image = False
          
    install_product_ids = fields.One2many("dtsc.installproductline","install_product_id")
    
class InstallproductLine(models.Model):
    _name = 'dtsc.installproductline'
    
    sequence = fields.Char(string='項')     
    install_product_id = fields.Many2one("dtsc.installproduct",ondelete='cascade')
    name = fields.Many2one("product.template",string="檔名") 
    size = fields.Char(string="尺寸") 
    caizhi = fields.Text(string="材質" ,compute="_compute_caizhi") 
    caishu = fields.Float(string="才數")
    shuliang = fields.Float(string="數量")
    gongdan = fields.Char(string="工單")
    product_atts = fields.Many2many("product.attribute.value",string="屬性名稱" )
    multi_chose_ids = fields.Char(string='後加工名稱')
    #make_order_id = fields.Many2one("dtsc.makein")
    
    @api.depends('multi_chose_ids', 'product_atts')
    def _compute_caizhi(self):
        for record in self:
            att_lines = []
            att_lines.append(record.name.name)
            for att in record.product_atts:
                # 获取属性名和属性值，并组合
                att_lines.append(f'{att.attribute_id.name}：{att.name}')
            
            if record.multi_chose_ids and record.multi_chose_ids != '[]':
                att_lines.append(f'後加工：{record.multi_chose_ids}')
            
            # 合并属性行
            combined_value = '\n'.join(att_lines)
            record.caizhi = combined_value