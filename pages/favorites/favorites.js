Page({
  data: {
    favorites: [],
    selectedItems: []
  },

  onLoad() {
    this.loadFavorites();
  },

  onShow() {
    this.loadFavorites();
  },

  // 加载收藏列表
  loadFavorites() {
    const favorites = wx.getStorageSync('favorites') || [];
    this.setData({ favorites });
  },

  // 查看菜谱详情
  viewRecipe(e) {
    const recipe = e.currentTarget.dataset.recipe;
    wx.navigateTo({
      url: `/pages/recipe/recipe?recipe=${encodeURIComponent(JSON.stringify(recipe))}`
    });
  },

  // 删除收藏
  removeFavorite(e) {
    const id = e.currentTarget.dataset.id;
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个收藏的菜谱吗？',
      success: (res) => {
        if (res.confirm) {
          const favorites = this.data.favorites.filter(item => item.id !== id);
          wx.setStorageSync('favorites', favorites);
          this.setData({ favorites });
          
          wx.showToast({
            title: '已删除',
            icon: 'success'
          });
        }
      }
    });
  },

  // 全选
  selectAll() {
    const selectedItems = this.data.favorites.map(item => item.id);
    this.setData({ selectedItems });
  },

  // 取消全选
  clearSelection() {
    this.setData({ selectedItems: [] });
  },

  // 删除选中项
  deleteSelected() {
    if (this.data.selectedItems.length === 0) {
      wx.showToast({
        title: '请选择要删除的菜谱',
        icon: 'none'
      });
      return;
    }

    wx.showModal({
      title: '确认删除',
      content: `确定要删除选中的${this.data.selectedItems.length}个菜谱吗？`,
      success: (res) => {
        if (res.confirm) {
          const favorites = this.data.favorites.filter(item => 
            !this.data.selectedItems.includes(item.id)
          );
          wx.setStorageSync('favorites', favorites);
          this.setData({ 
            favorites,
            selectedItems: []
          });
          
          wx.showToast({
            title: '删除成功',
            icon: 'success'
          });
        }
      }
    });
  },

  // 跳转到首页
  goToHome() {
    wx.switchTab({
      url: '/pages/index/index'
    });
  }
}) 