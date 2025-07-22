App({
  globalData: {
    // ChatGPT API配置
    openaiApiKey: '', // 请在此处填写您的OpenAI API密钥
    openaiApiUrl: 'https://api.openai.com/v1/chat/completions',
    
    // 服务器配置（预留）
    serverUrl: 'https://your-server.com/api',
    
  },

  onLaunch() {
    // 检查API密钥配置
    this.checkApiKey();
    
    // 初始化用户数据
    this.initUserData();
  },

  // 检查API密钥是否已配置
  checkApiKey() {
    const apiKey = this.globalData.openaiApiKey;
    if (!apiKey || apiKey === 'sk-your-openai-api-key-here') {
      wx.showModal({
        title: '配置提示',
        content: '请在app.js中配置OpenAI API密钥',
        showCancel: false
      });
    }
  },

  // 初始化用户数据
  initUserData() {
    // 初始化收藏列表
    if (!wx.getStorageSync('favorites')) {
      wx.setStorageSync('favorites', []);
    }
    
    // 初始化历史记录
    if (!wx.getStorageSync('history')) {
      wx.setStorageSync('history', []);
    }
  },

  // 获取API密钥
  getApiKey() {
    return this.globalData.openaiApiKey;
  },

  // 设置API密钥（预留方法，用于动态更新）
  setApiKey(apiKey) {
    this.globalData.openaiApiKey = apiKey;
  }
}) 