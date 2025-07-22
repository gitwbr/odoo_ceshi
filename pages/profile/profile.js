const app = getApp()

Page({
  data: {
    apiStatus: false,
    favoritesCount: 0,
    historyCount: 0,
    storageSize: 0
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    this.loadData();
  },

  // 加载数据
  loadData() {
    const apiKey = app.getApiKey();
    const favorites = wx.getStorageSync('favorites') || [];
    const history = wx.getStorageSync('history') || [];
    
    this.setData({
      apiStatus: !!apiKey && apiKey !== 'sk-your-openai-api-key-here',
      favoritesCount: favorites.length,
      historyCount: history.length
    });
    
    this.calculateStorageSize();
  },

  // 计算存储大小
  calculateStorageSize() {
    try {
      const info = wx.getStorageInfoSync();
      this.setData({
        storageSize: Math.round(info.currentSize / 1024)
      });
    } catch (error) {
      console.error('获取存储信息失败:', error);
    }
  },

  // 测试API连接
  testApiKey() {
    const apiKey = app.getApiKey();
    if (!apiKey || apiKey === 'sk-your-openai-api-key-here') {
      wx.showToast({
        title: '请先在app.js中配置API密钥',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '测试中...'
    });

    wx.request({
      url: app.globalData.openaiApiUrl,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      data: {
        model: 'gpt-4o',
        messages: [
          {
            role: 'user',
            content: '你好'
          }
        ],
        max_tokens: 10
      },
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200) {
          wx.showToast({
            title: 'API连接成功',
            icon: 'success'
          });
        } else {
          wx.showToast({
            title: 'API连接失败',
            icon: 'none'
          });
        }
      },
      fail: (error) => {
        wx.hideLoading();
        console.error('API测试失败:', error);
        wx.showToast({
          title: 'API连接失败',
          icon: 'none'
        });
      }
    });
  },

  // 打开OpenAI官网（预留功能）
  openOpenAI() {
    wx.setClipboardData({
      data: 'https://platform.openai.com/api-keys',
      success: () => {
        wx.showModal({
          title: '提示',
          content: 'OpenAI官网地址已复制到剪贴板，请在浏览器中打开',
          showCancel: false
        });
      }
    });
  },

  // 清空收藏
  clearFavorites() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有收藏的菜谱吗？',
      success: (res) => {
        if (res.confirm) {
          wx.setStorageSync('favorites', []);
          this.loadData();
          wx.showToast({
            title: '已清空收藏',
            icon: 'success'
          });
        }
      }
    });
  },

  // 清空历史
  clearHistory() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有历史记录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.setStorageSync('history', []);
          this.loadData();
          wx.showToast({
            title: '已清空历史',
            icon: 'success'
          });
        }
      }
    });
  },

  // 清空所有数据
  clearAllData() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有本地数据吗？这将包括收藏、历史记录等所有数据。',
      success: (res) => {
        if (res.confirm) {
          wx.clearStorageSync();
          this.loadData();
          wx.showToast({
            title: '已清空所有数据',
            icon: 'success'
          });
        }
      }
    });
  },

  // 联系我们
  contactUs() {
    wx.showModal({
      title: '联系我们',
      content: '如有问题或建议，请通过以下方式联系我们：\n\n邮箱：support@aicaipu.com\n微信：aicaipu_support',
      showCancel: false
    });
  }
}) 