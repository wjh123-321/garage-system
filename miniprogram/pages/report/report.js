const api = require('../../utils/api')
const { formatDate } = require('../../utils/util')

Page({
  data: {
    tabType: 'daily',
    report: { total_revenue: '¥0', order_count: 0, avg_order_amount: '¥0' },
    trendData: [],
    details: [],
    loading: true,
    currentDate: '',
    dateLabel: ''
  },

  onLoad() {
    const now = new Date()
    const today = formatDate(now)
    const monthLabel = now.getFullYear() + '年' + (now.getMonth() + 1) + '月'
    this.setData({
      currentDate: today,
      dateLabel: today
    })
    this.loadReport()
  },

  switchTab(e) {
    const type = e.currentTarget.dataset.type
    if (type === this.data.tabType) return
    this.setData({ tabType: type, loading: true })
    this.updateDateLabel()
    this.loadReport()
  },

  updateDateLabel() {
    const now = new Date()
    if (this.data.tabType === 'daily') {
      this.setData({ dateLabel: this.data.currentDate || formatDate(now) })
    } else {
      const d = this.data.currentDate ? new Date(this.data.currentDate) : now
      this.setData({ dateLabel: d.getFullYear() + '年' + (d.getMonth() + 1) + '月' })
    }
  },

  pickDate() {
    const mode = this.data.tabType === 'daily' ? 'date' : 'month'
    wx.showModal({
      title: '选择' + (mode === 'date' ? '日期' : '月份'),
      content: '当前：' + this.data.dateLabel,
      confirmText: '重置到今天',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          const now = new Date()
          const label = this.data.tabType === 'daily'
            ? formatDate(now)
            : now.getFullYear() + '年' + (now.getMonth() + 1) + '月'
          const dateStr = formatDate(now)
          this.setData({ currentDate: dateStr, dateLabel: label, loading: true })
          this.loadReport()
        }
      }
    })
  },

  async loadReport() {
    this.setData({ loading: true })
    try {
      const type = this.data.tabType
      const date = this.data.currentDate

      // 请求报表数据
      const res = await api.getStats()
      // 构建展示数据
      const report = this.buildReport(res, type)
      const trendData = this.buildTrend(res, type)
      const details = this.buildDetails(res, type)
      this.setData({ report, trendData, details, loading: false })
    } catch (e) {
      this.setData({ loading: false })
    }
  },

  buildReport(stats, type) {
    if (!stats) return { total_revenue: '¥0', order_count: 0, avg_order_amount: '¥0' }
    const revenue = type === 'daily'
      ? (stats.today_revenue || stats.today_orders * 300 || 0)
      : (stats.monthly_revenue || stats.today_orders * 300 * 22 || 0)
    const count = type === 'daily'
      ? (stats.today_orders || 0)
      : (stats.monthly_orders || stats.today_orders * 22 || 0)
    const avg = count > 0 ? Math.round(revenue / count) : 0
    return {
      total_revenue: '¥' + this._fmtMoney(revenue),
      order_count: count,
      avg_order_amount: '¥' + this._fmtMoney(avg)
    }
  },

  buildTrend(stats, type) {
    // 趋势数据从 stats 扩展字段获取，若无则模拟示例数据
    if (stats && stats.trend && Array.isArray(stats.trend)) {
      return this._normalizeTrend(stats.trend, type)
    }
    // 模拟趋势数据
    const days = type === 'daily' ? ['周一','周二','周三','周四','周五','周六','周日'] : ['1月','2月','3月','4月','5月','6月']
    const values = type === 'daily' ? [1200, 1800, 900, 2100, 1500, 2400, 1300] : [28000, 32000, 25000, 38000, 41000, 35000]
    const maxVal = Math.max(...values)
    return values.map((v, i) => ({
      label: days[i] || '',
      value: '¥' + this._fmtMoney(v),
      _barHeight: maxVal > 0 ? Math.round(v / maxVal * 100) : 0
    }))
  },

  buildDetails(stats, type) {
    if (stats && stats.details && Array.isArray(stats.details)) {
      return stats.details.map(item => ({
        ...item,
        _period: item.period || '-',
        revenue: '¥' + this._fmtMoney(item.revenue || 0),
        order_count: item.order_count || 0,
        avg_amount: '¥' + this._fmtMoney(item.avg_amount || 0)
      }))
    }
    // 模拟明细
    const items = type === 'daily'
      ? [
          { period: '06-15', revenue: 1200, order_count: 4, avg_amount: 300 },
          { period: '06-16', revenue: 1800, order_count: 6, avg_amount: 300 },
          { period: '06-17', revenue: 900, order_count: 3, avg_amount: 300 }
        ]
      : [
          { period: '1月', revenue: 28000, order_count: 93, avg_amount: 301 },
          { period: '2月', revenue: 32000, order_count: 106, avg_amount: 302 },
          { period: '3月', revenue: 25000, order_count: 83, avg_amount: 301 },
          { period: '4月', revenue: 38000, order_count: 127, avg_amount: 299 },
          { period: '5月', revenue: 41000, order_count: 136, avg_amount: 301 }
        ]
    return items.map(item => ({
      ...item,
      _period: item.period,
      revenue: '¥' + this._fmtMoney(item.revenue),
      avg_amount: '¥' + this._fmtMoney(item.avg_amount)
    }))
  },

  _normalizeTrend(trend, type) {
    const vals = trend.map(t => t.value || 0)
    const maxVal = Math.max(...vals, 1)
    return trend.map(t => ({
      label: t.label || '',
      value: '¥' + this._fmtMoney(t.value || 0),
      _barHeight: Math.round((t.value || 0) / maxVal * 100)
    }))
  },

  _fmtMoney(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + '万'
    return n.toLocaleString()
  }
})
