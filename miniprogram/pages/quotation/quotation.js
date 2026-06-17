const api = require('../../utils/api')
const { formatTime } = require('../../utils/util')

// 报价单状态映射
const QUOTATION_STATUS = {
  draft: { label: '草稿', class: '' },
  sent: { label: '已发送', class: 'sent' },
  accepted: { label: '已确认', class: 'accepted' },
  rejected: { label: '已拒绝', class: 'rejected' },
}

Page({
  data: {
    quotation: null,
    loading: true
  },

  onLoad(options) {
    if (options.id) {
      this.loadQuotation(Number(options.id))
    } else {
      wx.showToast({ title: '缺少报价单ID', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1500)
    }
  },

  async loadQuotation(id) {
    this.setData({ loading: true })
    try {
      const res = await api.getQuotation(id)
      const q = res.data || res
      // 计算展示字段
      const st = QUOTATION_STATUS[q.status] || { label: q.status, class: '' }
      q._statusLabel = st.label
      q._statusClass = st.class
      q._createdAt = formatTime(q.created_at)
      // 确保金额保留两位小数
      q.total_amount = Number(q.total_amount).toFixed(2)
      q.items = (q.items || []).map(item => ({
        ...item,
        unit_price: Number(item.unit_price).toFixed(2),
        total: Number(item.total).toFixed(2)
      }))
      this.setData({ quotation: q, loading: false })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载报价单失败', icon: 'none' })
    }
  },

  onSendToCustomer() {
    const q = this.data.quotation
    if (!q) return
    wx.showModal({
      title: '发送给客户',
      content: `将报价单 ${q.quotation_no} 发送给 ${q.customer_name}（${q.customer_phone}）？`,
      success: (res) => {
        if (res.confirm) {
          this._doSend(q)
        }
      }
    })
  },

  async _doSend(q) {
    wx.showLoading({ title: '发送中...' })
    try {
      // 调用后端发送接口（模拟：暂未实现真实发送，仅更新状态）
      // const result = await api.sendQuotation(q.id)
      // 模拟发送成功
      await new Promise(resolve => setTimeout(resolve, 1000))
      wx.hideLoading()
      wx.showToast({ title: '已发送给客户', icon: 'success' })
      // 更新本地状态
      if (q.status === 'draft') {
        q.status = 'sent'
        q._statusLabel = '已发送'
        q._statusClass = 'sent'
        this.setData({ quotation: q })
      }
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '发送失败，请重试', icon: 'none' })
    }
  },

  onShare() {
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage', 'shareTimeline']
    })
    wx.showToast({ title: '请点击右上角转发', icon: 'none' })
  },

  // 允许分享
  onShareAppMessage() {
    const q = this.data.quotation
    if (!q) return {}
    return {
      title: `报价单 ${q.quotation_no} - ${q.customer_name} ${q.car_plate}`,
      path: `/pages/quotation/quotation?id=${q.id}`
    }
  }
})
