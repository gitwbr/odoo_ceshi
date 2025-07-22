const app = getApp()

Page({
  data: {
    recipe: {},
    isFavorite: false,
    originalNutrition: {}
  },

  onLoad(options) {
    if (options.recipe) {
      const recipe = JSON.parse(decodeURIComponent(options.recipe));
      // 初始化每个食材的weight和unit
      if (recipe.ingredients) {
        recipe.ingredients.forEach(item => {
          // weight
          if (!item.weight) {
            const match = item.amount && item.amount.match(/\d+/);
            if (match) {
              item.weight = parseInt(match[0]);
            } else {
              item.weight = '';
            }
          }
          // unit
          if (!item.unit) {
            const unitMatch = item.amount && item.amount.replace(/\d+/g, '');
            item.unit = unitMatch && unitMatch.trim() ? unitMatch.trim() : 'g';
          }
        });
      }
      this.setData({
        recipe,
        originalNutrition: { ...recipe.nutrition }
      }, () => {
        this.recalculateNutrition();
      });
      this.checkFavoriteStatus();
    }
  },

  // 检查收藏状态
  checkFavoriteStatus() {
    const favorites = wx.getStorageSync('favorites') || [];
    const isFavorite = favorites.some(item => item.id === this.data.recipe.id);
    this.setData({ isFavorite });
  },

  // 切换收藏状态
  toggleFavorite() {
    const favorites = wx.getStorageSync('favorites') || [];
    const recipe = this.data.recipe;
    
    if (this.data.isFavorite) {
      // 取消收藏
      const newFavorites = favorites.filter(item => item.id !== recipe.id);
      wx.setStorageSync('favorites', newFavorites);
      this.setData({ isFavorite: false });
      wx.showToast({
        title: '已取消收藏',
        icon: 'success'
      });
    } else {
      // 添加收藏
      favorites.unshift(recipe);
      wx.setStorageSync('favorites', favorites);
      this.setData({ isFavorite: true });
      wx.showToast({
        title: '已添加到收藏',
        icon: 'success'
      });
    }
  },

  // 重新计算营养信息
  recalculateNutrition() {
    function parseNutritionValue(val) {
      if (typeof val === 'number') return val;
      if (!val) return 0;
      const match = String(val).match(/-?\d+(\.\d+)?/);
      return match ? parseFloat(match[0]) : 0;
    }
    const recipe = this.data.recipe;
    let totalCalories = 0, totalProtein = 0, totalFat = 0, totalCarbs = 0;
    recipe.ingredients.forEach(item => {
      // Unify nutrition data source for WXML
      item.nutritionInfo = item.nutrition_per_100g || item.nutrition || {};

      // Add a flag to control UI visibility
      const match = item.amount && String(item.amount).match(/\d+/);
      item.hasNumericAmount = !!match;
      const amount = match ? parseFloat(match[0]) : null;

      const nutritionData = item.nutritionInfo;
      if (nutritionData) {
        if (item.hasNumericAmount && amount !== null) {
          item.actualNutrition = {
            calories: Math.round((amount / 100) * parseNutritionValue(nutritionData.calories)),
            protein: Math.round((amount / 100) * parseNutritionValue(nutritionData.protein) * 10) / 10,
            fat: Math.round((amount / 100) * parseNutritionValue(nutritionData.fat) * 10) / 10,
            carbs: Math.round((amount / 100) * (parseNutritionValue(nutritionData.carbohydrates) || parseNutritionValue(nutritionData.carbs)) * 10) / 10
          };
          totalCalories += item.actualNutrition.calories;
          totalProtein += item.actualNutrition.protein;
          totalFat += item.actualNutrition.fat;
          totalCarbs += item.actualNutrition.carbs;
        } else {
          item.actualNutrition = null;
        }
      }
    });
    recipe.nutrition = {
      calories: Math.round(totalCalories),
      protein: Math.round(totalProtein * 10) / 10,
      fat: Math.round(totalFat * 10) / 10,
      carbs: Math.round(totalCarbs * 10) / 10
    };
    this.setData({ recipe });
  },

  // 更新食材重量（实时计算营养）
  updateIngredientWeight(e) {
    const index = e.currentTarget.dataset.index;
    const newWeight = parseInt(e.detail.value) || 0;
    const recipe = this.data.recipe;
    const ingredient = recipe.ingredients[index];
    
    ingredient.weight = newWeight;
    ingredient.amount = newWeight + (ingredient.unit || 'g'); // Keep amount and weight in sync

    this.setData({ recipe }, () => {
      this.recalculateNutrition();
    });
  },

  // 分享菜谱
  shareRecipe() {
    const recipe = this.data.recipe;
    const shareText = `${recipe.name}\n\n${recipe.description}\n\n营养信息：\n热量：${recipe.nutrition.calories}千卡\n蛋白质：${recipe.nutrition.protein}g\n脂肪：${recipe.nutrition.fat}g\n碳水化合物：${recipe.nutrition.carbs}g\n\n食材：\n${recipe.ingredients.map(item => `${item.name} ${item.amount}`).join('\n')}\n\n制作步骤：\n${recipe.steps.map((step, i) => `${i + 1}. ${step}`).join('\n')}\n\n小贴士：${recipe.tips ? recipe.tips : ''}`;
    
    wx.setClipboardData({
      data: shareText,
      success: () => {
        wx.showToast({
          title: '菜谱已复制到剪贴板',
          icon: 'success'
        });
      }
    });
  },

  // 保存到服务器（预留功能）
  saveToServer() {
    const recipe = this.data.recipe;
    
    // 这里预留服务器保存功能
    // 用户需要自己实现服务器端API
    wx.showModal({
      title: '功能提示',
      content: '此功能需要配置服务器端API，请根据您的服务器实现相应的保存逻辑。',
      showCancel: false
    });
    
    // 示例代码（需要根据实际服务器API调整）
    /*
    wx.request({
      url: app.globalData.serverUrl + '/recipes',
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: recipe,
      success: (res) => {
        wx.showToast({
          title: '保存成功',
          icon: 'success'
        });
      },
      fail: (error) => {
        wx.showToast({
          title: '保存失败',
          icon: 'none'
        });
      }
    });
    */
  },

  // 页面分享
  onShareAppMessage() {
    const recipe = this.data.recipe;
    return {
      title: recipe.name,
      desc: recipe.description,
      path: `/pages/recipe/recipe?recipe=${encodeURIComponent(JSON.stringify(recipe))}`
    };
  },

  // 分享到朋友圈
  onShareTimeline() {
    const recipe = this.data.recipe;
    return {
      title: recipe.name,
      query: `recipe=${encodeURIComponent(JSON.stringify(recipe))}`
    };
  }
}) 