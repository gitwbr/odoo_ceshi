# AI菜谱助手 - 微信小程序

一款基于人工智能的菜谱生成微信小程序，帮助用户轻松制作美味佳肴。

## 功能特点

### 🎯 核心功能
- **AI菜谱生成**：使用ChatGPT API生成个性化菜谱
- **多种生成方式**：
  - 随机生成菜谱
  - 根据选择食材生成菜谱
  - 根据菜系类型生成菜谱（川菜、粤菜、淮扬菜等）
- **营养计算**：自动计算三大营养素含量和总热量
- **食材重量调整**：支持实时调整食材重量并重新计算营养

### 📱 用户体验
- **详细制作步骤**：提供清晰的烹饪指导
- **收藏功能**：收藏喜欢的菜谱
- **分享功能**：分享菜谱给朋友
- **历史记录**：查看最近生成的菜谱
- **响应式设计**：适配不同屏幕尺寸

### 🎨 界面设计
- **现代化UI**：采用渐变色彩和卡片式设计
- **直观操作**：简单易用的交互界面
- **加载动画**：提供良好的用户体验

## 技术架构

### 前端技术
- **微信小程序原生开发**
- **WXML + WXSS + JavaScript**
- **响应式设计**

### AI集成
- **OpenAI ChatGPT API**
- **JSON格式数据解析**
- **智能营养计算**

### 数据存储
- **本地存储**：使用微信小程序Storage API
- **云端存储**：预留服务器端API接口

## 项目结构

```
caipu/
├── app.js                 # 小程序入口文件
├── app.json              # 小程序配置文件
├── app.wxss              # 全局样式文件
├── sitemap.json          # 站点地图配置
├── project.config.json   # 项目配置
├── README.md             # 项目说明文档
├── pages/                # 页面目录
│   ├── index/           # 首页
│   │   ├── index.wxml
│   │   ├── index.js
│   │   └── index.wxss
│   ├── recipe/          # 菜谱详情页
│   │   ├── recipe.wxml
│   │   ├── recipe.js
│   │   └── recipe.wxss
│   ├── favorites/       # 收藏页面
│   │   ├── favorites.wxml
│   │   ├── favorites.js
│   │   └── favorites.wxss
│   └── profile/         # 个人中心
│       ├── profile.wxml
│       ├── profile.js
│       └── profile.wxss
└── images/              # 图片资源目录
    ├── home.png
    ├── home-active.png
    ├── favorite.png
    ├── favorite-active.png
    ├── profile.png
    ├── profile-active.png
    ├── heart.png
    └── heart-filled.png
```

## 安装和配置

### 1. 获取OpenAI API密钥
1. 访问 [OpenAI官网](https://platform.openai.com/api-keys)
2. 注册账号并获取API密钥
3. 确保有足够的API调用额度

### 2. 配置小程序
1. 下载微信开发者工具
2. 导入项目到微信开发者工具
3. 在`project.config.json`中配置您的小程序AppID
4. 在`app.js`中配置OpenAI API密钥

### 3. 服务器端配置（可选）
如需使用云端存储功能，需要配置服务器端API：
- 修改`app.js`中的`serverUrl`配置
- 实现相应的API接口
- 在`pages/recipe/recipe.js`中取消注释服务器保存代码

## 使用说明

### 基本使用流程
1. **配置API密钥**：在`app.js`中配置OpenAI API密钥
2. **生成菜谱**：
   - 点击"随机菜谱"快速生成
   - 选择食材生成个性化菜谱
   - 选择菜系生成特定风格菜谱
3. **查看详情**：点击生成的菜谱查看详细信息
4. **收藏分享**：收藏喜欢的菜谱或分享给朋友
5. **调整营养**：在菜谱详情页调整食材重量

### 功能详解

#### AI菜谱生成
- **随机生成**：AI根据当前流行趋势和用户偏好生成菜谱
- **食材选择**：用户选择现有食材，AI生成合适的菜谱
- **菜系选择**：根据中国八大菜系特点生成相应菜谱

#### 营养计算
- **自动计算**：根据食材数据库自动计算营养成分
- **实时调整**：支持调整食材重量，实时重新计算营养
- **详细显示**：显示热量、蛋白质、脂肪、碳水化合物含量

#### 数据管理
- **本地存储**：收藏和历史记录存储在本地
- **云端同步**：预留服务器端API接口（需自行实现）
- **数据清理**：支持清空收藏、历史记录等操作

## 自定义配置

### 添加新食材
在`app.js`的`globalData.ingredients`数组中添加新食材：
```javascript
{
  name: '食材名称',
  category: '分类',
  calories: 热量,
  protein: 蛋白质,
  fat: 脂肪,
  carbs: 碳水化合物
}
```

### 添加新菜系
在`app.js`的`globalData.cuisineTypes`数组中添加新菜系：
```javascript
{
  name: '菜系名称',
  description: '菜系描述'
}
```

### 修改API配置
- 修改`app.js`中的`openaiApiKey`可更换API密钥
- 修改`app.js`中的`openaiApiUrl`可更换API端点
- 修改`app.js`中的`serverUrl`可配置服务器地址

## 注意事项

### API使用
- 确保OpenAI API密钥有效且有足够额度
- 建议设置API调用频率限制
- 注意API响应时间，提供适当的加载提示

### 数据安全
- API密钥仅存储在本地，不会上传到服务器
- 用户数据仅存储在本地，保护用户隐私
- 如需云端存储，请实现相应的安全措施

### 性能优化
- 合理使用本地存储，避免存储过多数据
- 优化API调用频率，减少不必要的请求
- 使用适当的缓存策略

## 开发计划

### 已实现功能
- ✅ AI菜谱生成
- ✅ 营养计算
- ✅ 收藏功能
- ✅ 分享功能
- ✅ 历史记录
- ✅ 食材重量调整

### 计划功能
- 🔄 图片生成（需要DALL-E API）
- 🔄 语音播报
- 🔄 购物清单生成
- 🔄 用户评分系统
- 🔄 更多菜系支持

## 技术支持

如有问题或建议，请联系：
- 邮箱：support@aicaipu.com
- 微信：aicaipu_support

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现基础AI菜谱生成功能
- 支持营养计算和收藏功能
- 完成响应式UI设计 