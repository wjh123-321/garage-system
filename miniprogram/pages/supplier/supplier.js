const api = require('../../utils/api')

Page({
  data: {
    suppliers: [],
    page: 1,
    loading: false,
    keyword: '',
    hasMore: true,
    _showEmpty: false
  },
  onLoad() { this.loadSuppliers(true) },
  async loadSuppliers(refresh) {
    if (refresh === undefined) refresh = false
    if (this.data.loading) return
    this.setData({ loading: true })
    if (refresh) this.setData({ page: 1, suppliers: [] })
    try {
      const params = { page: this.data.page, page_size: 20 }
      if (this.data.keyword) params.keyword = this.data.keyword
      const res = await api.getSuppliers(params)
      const items = res.items || res.data || []
      var computedItems = items.map(function(item) {
        var status = item.status || 'active'
        return {
          ...item,
          _statusLabel: status === 'active' ? '合作中' : '已停用',
          _statusClass: status === 'active' ? 'active' : 'inactive'
        }
      })
      this.setData({
        suppliers: refresh ? computedItems : [...this.data.suppliers, ...computedItems],
        hasMore: items.length >= 20,
        page: this.data.page + 1,
        _showEmpty: computedItems.length === 0,
        loading: false
      })
    } catch(e) { this.setData({ loading: false }) }
  },
  search(e) {
    this.setData({ keyword: e.detail.value })
    this.loadSuppliers(true)
  },
  goDetail(e) {
    wx.navigateTo({ url: '/pages/supplier/detail/detail?id=' + e.currentTarget.dataset.id })
  },
  goCreate() {
    wx.navigateTo({ url: '/pages/supplier/detail/detail' })
  }
})
