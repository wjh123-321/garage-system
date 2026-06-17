const api = require('../../utils/api')

Page({
  data: {
    // 导航层级: brand / model / category / parts / detail
    currentLevel: 'brand',

    // 品牌
    brandSearch: '',
    brands: [],
    brandLoading: false,

    // 车型
    selectedBrand: null,
    models: [],
    modelLoading: false,

    // 分类
    selectedModel: null,
    categories: [],
    categoryLoading: false,

    // 配件列表
    selectedCategory: null,
    parts: [],
    partsLoading: false,

    // 配件详情
    selectedPart: null,
    detailLoading: false
  },

  onBrandSearchInput(e) {
    this.setData({ brandSearch: e.detail.value })
  },

  async onBrandSearch() {
    const keyword = this.data.brandSearch.trim()
    if (!keyword) {
      wx.showToast({ title: '请输入品牌名称', icon: 'none' })
      return
    }
    this.setData({ brandLoading: true })
    try {
      const res = await api.getPartsStoreBrands({ keyword })
      const items = res.brands || res.data || res.items || res || []
      this.setData({
        brands: Array.isArray(items) ? items.map(b => ({
          ...b,
          _label: b.name || b.brand || b.brand_name || ''
        })) : [],
        brandLoading: false,
        currentLevel: 'brand'
      })
    } catch (e) {
      this.setData({ brands: [], brandLoading: false })
    }
  },

  async selectBrand(e) {
    const brand = e.currentTarget.dataset.brand
    this.setData({ selectedBrand: brand, modelLoading: true, currentLevel: 'model' })
    try {
      const res = await api.getPartsStoreModels(brand._label)
      const items = res.models || res.data || res.items || res || []
      this.setData({
        models: Array.isArray(items) ? items.map(m => ({
          ...m,
          _label: m.name || m.model || m.model_name || m.full_name || ''
        })) : [],
        modelLoading: false
      })
    } catch (e) {
      this.setData({ models: [], modelLoading: false })
    }
  },

  async selectModel(e) {
    const model = e.currentTarget.dataset.model
    this.setData({ selectedModel: model, categoryLoading: true, currentLevel: 'category' })
    try {
      const res = await api.searchPartsStore({
        brand: this.data.selectedBrand._label,
        model: model._label,
        type: 'categories'
      })
      const items = res.categories || res.data || res.items || res || []
      this.setData({
        categories: Array.isArray(items) ? items.map(c => ({
          ...c,
          _label: c.name || c.category || c.category_name || ''
        })) : [],
        categoryLoading: false
      })
    } catch (e) {
      this.setData({ categories: [], categoryLoading: false })
    }
  },

  async selectCategory(e) {
    const category = e.currentTarget.dataset.category
    this.setData({ selectedCategory: category, partsLoading: true, currentLevel: 'parts' })
    try {
      const res = await api.searchPartsStore({
        brand: this.data.selectedBrand._label,
        model: this.data.selectedModel._label,
        category: category._label
      })
      const items = res.parts || res.data || res.items || res || []
      this.setData({
        parts: Array.isArray(items) ? items.map(p => ({
          ...p,
          _label: p.name || p.part_name || p.part || ''
        })) : [],
        partsLoading: false
      })
    } catch (e) {
      this.setData({ parts: [], partsLoading: false })
    }
  },

  async showPartDetail(e) {
    const part = e.currentTarget.dataset.part
    this.setData({ detailLoading: true, currentLevel: 'detail' })
    try {
      const res = await api.getPartDetail({ part_id: part.id || part._label })
      this.setData({
        selectedPart: {
          ...res,
          name: res.name || part._label,
          oe_no: res.oe_no || res.oe || res.oe_number || part.oe_no || '--',
          brand_suggestion: res.brand_suggestion || res.brand || res.suggested_brand || '--',
          reference_price: res.reference_price || res.price || res.retail_price || 0,
          spec: res.spec || part.spec || '--',
          unit: res.unit || part.unit || '个'
        },
        detailLoading: false
      })
    } catch (e) {
      this.setData({
        selectedPart: {
          name: part._label,
          oe_no: part.oe_no || '--',
          brand_suggestion: '--',
          reference_price: 0,
          spec: part.spec || '--',
          unit: part.unit || '个'
        },
        detailLoading: false
      })
    }
  },

  // 返回上一级
  goBack() {
    const levelMap = {
      detail: 'parts',
      parts: 'category',
      category: 'model',
      model: 'brand'
    }
    const prev = levelMap[this.data.currentLevel]
    this.setData({ currentLevel: prev || 'brand' })
  },

  // 重新选择品牌（回到根）
  goHome() {
    this.setData({
      currentLevel: 'brand',
      selectedBrand: null,
      selectedModel: null,
      selectedCategory: null,
      selectedPart: null,
      brands: [],
      models: [],
      categories: [],
      parts: []
    })
  },

  // 扫VIN查配件
  scanVin() {
    wx.scanCode({
      success: (res) => {
        const vin = res.result
        if (!vin || vin.length < 11) {
          wx.showToast({ title: '无效VIN码', icon: 'none' })
          return
        }
        this.decodeVinParts(vin)
      },
      fail: () => {
        wx.showToast({ title: '扫码失败', icon: 'none' })
      }
    })
  },

  async decodeVinParts(vin) {
    wx.showLoading({ title: '解析VIN中...' })
    try {
      const res = await api.getPartsByVin(vin)
      const parts = res.parts || res.data || res.items || res || []
      this.setData({
        currentLevel: 'parts',
        selectedBrand: { name: res.brand || res.make || '' },
        selectedModel: { name: res.model || '' },
        selectedCategory: null,
        parts: Array.isArray(parts) ? parts.map(p => ({
          ...p,
          _label: p.name || p.part_name || ''
        })) : [],
        detailLoading: false
      })
      wx.hideLoading()
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '未查询到配件', icon: 'none' })
    }
  },

  // 手动输入VIN
  inputVinManually() {
    wx.showModal({
      title: '输入VIN码',
      editable: true,
      placeholderText: '请输入17位VIN码',
      success: (res) => {
        if (res.confirm && res.content) {
          this.decodeVinParts(res.content.trim().toUpperCase())
        }
      }
    })
  }
})
