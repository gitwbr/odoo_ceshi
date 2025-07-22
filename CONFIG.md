# AI菜谱助手 - 配置说明

## 快速开始

### 1. 获取OpenAI API密钥

1. 访问 [OpenAI官网](https://platform.openai.com/api-keys)
2. 注册或登录您的OpenAI账号
3. 点击"Create new secret key"创建新的API密钥
4. 复制生成的密钥（注意：密钥只显示一次）

### 2. 配置小程序

1. 下载并安装[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开微信开发者工具，选择"导入项目"
3. 选择本项目的根目录
4. 在`project.config.json`中修改`appid`为您的小程序AppID

### 3. 配置API密钥

1. 打开`app.js`文件
2. 找到`globalData`中的`openaiApiKey`配置项
3. 将`'sk-your-openai-api-key-here'`替换为您的实际API密钥
4. 保存文件后重新编译小程序

## 详细配置

### 小程序AppID配置

在`project.config.json`文件中修改：
```json
{
  "appid": "your-app-id-here"
}
```

### API配置

在`app.js`文件中可以修改以下配置：

```javascript
globalData: {
  // ChatGPT API配置
  openaiApiKey: 'sk-your-openai-api-key-here', // 请在此处填写您的OpenAI API密钥
  openaiApiUrl: 'https://api.openai.com/v1/chat/completions',
  
  // 服务器配置（预留）
  serverUrl: 'https://your-server.com/api',
  
  // 其他配置...
}
```

### 食材数据库配置

在`app.js`的`globalData.ingredients`数组中添加或修改食材：

```javascript
ingredients: [
  {
    name: '食材名称',
    category: '分类', // 如：肉类、蔬菜、主食等
    calories: 143,    // 每100g的热量(kcal)
    protein: 20.3,    // 每100g的蛋白质(g)
    fat: 6.2,         // 每100g的脂肪(g)
    carbs: 0          // 每100g的碳水化合物(g)
  }
]
```

### 菜系配置

在`app.js`的`globalData.cuisineTypes`数组中添加或修改菜系：

```javascript
cuisineTypes: [
  {
    name: '菜系名称',
    description: '菜系描述'
  }
]
```

## 服务器端配置（可选）

如果您有自己的云服务器，可以实现以下API接口来支持云端存储功能：

### 1. 保存菜谱API

**接口地址：** `POST /api/recipes`

**请求参数：**
```json
{
  "id": "菜谱ID",
  "name": "菜谱名称",
  "description": "菜谱描述",
  "ingredients": [
    {
      "name": "食材名称",
      "amount": "用量"
    }
  ],
  "steps": ["步骤1", "步骤2"],
  "nutrition": {
    "calories": 300,
    "protein": 25,
    "fat": 15,
    "carbs": 20
  },
  "tags": ["标签1", "标签2"],
  "tips": "烹饪技巧",
  "createTime": "2024-01-01T00:00:00.000Z"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "保存成功",
  "data": {
    "id": "菜谱ID"
  }
}
```

### 2. 获取菜谱列表API

**接口地址：** `GET /api/recipes`

**请求参数：**
```
page: 页码
limit: 每页数量
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "recipes": [...],
    "total": 100,
    "page": 1,
    "limit": 10
  }
}
```

### 3. 删除菜谱API

**接口地址：** `DELETE /api/recipes/:id`

**响应示例：**
```json
{
  "success": true,
  "message": "删除成功"
}
```

## 数据库设计建议

如果您要实现服务器端功能，建议使用以下数据库表结构：

### 菜谱表 (recipes)
```sql
CREATE TABLE recipes (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  ingredients JSON,
  steps JSON,
  nutrition JSON,
  tags JSON,
  tips TEXT,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 用户表 (users)
```sql
CREATE TABLE users (
  id VARCHAR(50) PRIMARY KEY,
  openid VARCHAR(100) UNIQUE,
  nickname VARCHAR(50),
  avatar VARCHAR(200),
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 收藏表 (favorites)
```sql
CREATE TABLE favorites (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(50),
  recipe_id VARCHAR(50),
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (recipe_id) REFERENCES recipes(id)
);
```

## 安全配置

### 1. API密钥安全
- 不要在代码中硬编码API密钥
- 使用环境变量或配置文件存储敏感信息
- 定期更换API密钥

### 2. 数据验证
- 对用户输入进行验证和过滤
- 防止SQL注入和XSS攻击
- 使用HTTPS协议

### 3. 访问控制
- 实现用户身份验证
- 设置API访问频率限制
- 记录API调用日志

## 性能优化

### 1. 缓存策略
- 使用Redis缓存热门菜谱
- 实现CDN加速静态资源
- 合理设置缓存过期时间

### 2. 数据库优化
- 为常用查询字段创建索引
- 使用分页查询避免大量数据加载
- 定期清理无用数据

### 3. 前端优化
- 压缩和合并CSS/JS文件
- 使用图片懒加载
- 实现虚拟滚动优化长列表

## 常见问题

### Q: API调用失败怎么办？
A: 检查以下几点：
1. 在`app.js`中是否正确配置了API密钥
2. 网络连接是否正常
3. API调用额度是否充足
4. 请求参数是否正确

### Q: 如何修改API密钥？
A: 直接编辑`app.js`文件中的`globalData.openaiApiKey`配置项，将`'sk-your-openai-api-key-here'`替换为您的实际API密钥。

### Q: 如何添加新的食材？
A: 在`app.js`的`globalData.ingredients`数组中添加新食材，包含名称、分类和营养成分信息。

### Q: 如何修改菜系？
A: 在`app.js`的`globalData.cuisineTypes`数组中修改或添加菜系信息。

### Q: 如何实现云端存储？
A: 参考上面的服务器端配置说明，实现相应的API接口，然后修改小程序中的相关代码。

## 技术支持

如果您在配置过程中遇到问题，可以：
1. 查看微信开发者工具的控制台日志
2. 检查网络请求是否成功
3. 验证API密钥是否有效
4. 联系技术支持团队

---

**注意：** 请确保遵守OpenAI的使用条款和微信小程序的开发规范。 