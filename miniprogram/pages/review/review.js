const api = require('../../utils/api')

Page({
  data: {
    orderId: '',
    rating: 0,
    comment: '',
    reviews: [],
    loading: false,
    submitting: false,
    stars: [1, 2, 3, 4, 5]
  },

  onLoad(options) {
    if (options.order_id) {
      this.setData({ orderId: options.order_id })
      this.loadReviews(options.order_id)
    }
  },

  async loadReviews(orderId) {
    this.setData({ loading: true })
    try {
      const res = await api.getReviews(orderId)
      this.setData({ reviews: Array.isArray(res) ? res : [] })
    } catch (e) {
      wx.showToast({ title: '加载评价失败', icon: 'none' })
    }
    this.setData({ loading: false })
  },

  onOrderIdInput(e) {
    this.setData({ orderId: e.detail.value })
  },

  onCommentInput(e) {
    this.setData({ comment: e.detail.value })
  },

  selectStar(e) {
    const star = e.currentTarget.dataset.star
    this.setData({ rating: star })
  },

  async submit() {
    const { orderId, rating, comment } = this.data
    if (!orderId) {
      wx.showToast({ title: '请输入工单ID', icon: 'none' })
      return
    }
    if (rating === 0) {
      wx.showToast({ title: '请选择评分', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    try {
      await api.createReview({ order_id: parseInt(orderId), rating, comment })
      wx.showToast({ title: '评价成功', icon: 'success' })
      this.setData({ rating: 0, comment: '' })
      this.loadReviews(orderId)
    } catch (e) {
      wx.showToast({ title: '提交失败', icon: 'none' })
    }
    this.setData({ submitting: false })
  },

  onShareAppMessage() {
    return { title: '客户评价' }
  }
})
