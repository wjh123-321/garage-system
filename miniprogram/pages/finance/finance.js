const api = require('../../utils/api')
const { formatTime } = require('../../utils/util')

Page({
  data: {
    // 汇总数据
    summary: {
      total_revenue: 0,       // 总营收
      work_order_income: 0,   // 工单收入
      parts_expense: 0,       // 配件支出
      net_profit: 0           // 净利润
    },
    // 日期筛选
    dateRange: {
      start: '',
      end: ''
    },
    dateLabel: '本月',
    showDatePicker: false,
    // 明细列表
    details: [],
    loading: true,
    hasMore: true,
    page: 1,
    pageSize: 20,
    _showEmpty: false,
    _showError: false,
    _errorMsg: ''
  },

  onLoad() {
    const now = new Date()
    const start = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-01'
    const end = this._todayStr()
    this.setData({
      'dateRange.start': start,
      'dateRange.end': end
    })
    this.loadData()
  },

  onShow() {
    if (this.data.details.length > 0) {
      this.loadSummary()
    }
  },

  _todayStr() {
    const d = new Date()
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
  },

  _formatDateLabel(start, end) {
    if (!start && !end) return '全部'
    if (start && !end) return start + ' 起'
    if (!start && end) return end + ' 止'
    const s = start.slice(5)
    const e = end.slice(5)
    if (start.slice(0, 4) === end.slice(0, 4)) {
      if (start === end) return start
      if (s.slice(0, 2) === e.slice(0, 2)) return start + '~' + e.slice(3)
      return s + ' ~ ' + e
    }
    return start + ' ~ ' + end
  },

  _buildSummaryFromDetails(details) {
    const s = { total_revenue: 0, work_order_income: 0, parts_expense: 0, net_profit: 0 }
    details.forEach(function(item) {
      const amount = Number(item.amount) || 0
      s.total_revenue += amount
      if (item.type === 'income') {
        s.work_order_income += amount
      } else if (item.type === 'expense') {
        s.parts_expense += amount
      }
    })
    s.net_profit = s.work_order_income - s.parts_expense
    s.total_revenue = s.work_order_income + s.parts_expense
    return s
  },

  async loadData() {
    this.setData({ loading: true, _showError: false, _showEmpty: false, page: 1, hasMore: true })
    try {
      const [summary, details] = await Promise.all([
        this._fetchSummary(),
        this._fetchDetails(1)
      ])
      const list = (details.items || details.data || details.records || []).map(this._computeItemDisplay.bind(this))
      this.setData({
        summary: summary || this._buildSummaryFromDetails(list),
        details: list,
        loading: false,
        _showEmpty: list.length === 0
      })
    } catch (e) {
      console.error('财务数据加载失败', e)
      this.setData({
        loading: false,
        _showError: true,
        _showEmpty: false,
        _errorMsg: '数据加载失败，下拉刷新重试'
      })
    }
  },

  async loadSummary() {
    try {
      const summary = await this._fetchSummary()
      if (summary) {
        this.setData({ summary: summary })
      }
    } catch (_) {}
  },

  async _fetchSummary() {
    try {
      const res = await api.request('/finance/summary', 'GET', {
        start_date: this.data.dateRange.start,
        end_date: this.data.dateRange.end
      })
      return res
    } catch (_) {
      return null
    }
  },

  async _fetchDetails(page) {
    try {
      const res = await api.request('/finance/details', 'GET', {
        start_date: this.data.dateRange.start,
        end_date: this.data.dateRange.end,
        page: page,
        page_size: this.data.pageSize
      })
      return res
    } catch (_) {
      return {}
    }
  },

  _computeItemDisplay(item) {
    const amount = Number(item.amount) || 0
    const isIncome = item.type === 'income'
    return {
      _id: item.id || item._id,
      _type: item.type || 'income',
      _typeLabel: isIncome ? '工单收入' : '配件支出',
      _typeIcon: isIncome ? '💵' : '🔩',
      _amount: '¥' + amount.toFixed(2),
      _amountClass: isIncome ? 'income' : 'expense',
      _desc: item.description || item.remark || item.order_no || '',
      _time: formatTime(item.created_at || item.date || item.time),
      _orderNo: item.order_no || ''
    }
  },

  // 加载更多
  async loadMore() {
    if (this.data.loading || !this.data.hasMore) return
    this.setData({ loading: true })
    try {
      const nextPage = this.data.page + 1
      const res = await this._fetchDetails(nextPage)
      const items = (res.items || res.data || res.records || [])
      if (items.length === 0) {
        this.setData({ hasMore: false, loading: false })
        return
      }
      const more = items.map(this._computeItemDisplay.bind(this))
      this.setData({
        details: this.data.details.concat(more),
        page: nextPage,
        hasMore: items.length >= this.data.pageSize,
        loading: false
      })
    } catch (_) {
      this.setData({ loading: false })
    }
  },

  // 选择日期范围
  onDateTap() {
    wx.showModal({
      title: '选择日期范围',
      editable: true,
      placeholderText: '格式: YYYY-MM-DD ~ YYYY-MM-DD',
      content: this.data.dateRange.start + ' ~ ' + this.data.dateRange.end,
      success: function(res) {
        if (res.confirm && res.content) {
          const parts = res.content.split('~').map(function(s) { return s.trim() })
          var start = parts[0] || ''
          var end = parts[1] || ''
          this.setData({
            'dateRange.start': start,
            'dateRange.end': end,
            dateLabel: this._formatDateLabel(start, end)
          })
          this.loadData()
        }
      }.bind(this)
    })
  },

  // 快捷筛选
  onQuickFilter(e) {
    const range = e.currentTarget.dataset.range
    var start, end = this._todayStr()
    var label = ''
    switch (range) {
      case 'today':
        start = end
        label = '今天'
        break
      case 'yesterday': {
        var d = new Date()
        d.setDate(d.getDate() - 1)
        start = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
        end = start
        label = '昨天'
        break
      }
      case 'week': {
        var d = new Date()
        d.setDate(d.getDate() - d.getDay() + 1)
        start = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
        label = '本周'
        break
      }
      case 'month':
        start = end.slice(0, 7) + '-01'
        label = '本月'
        break
      case 'quarter':
        start = end.slice(0, 4) + '-' + String(Math.floor((new Date().getMonth()) / 3) * 3 + 1).padStart(2, '0') + '-01'
        label = '本季度'
        break
      default:
        start = ''
        end = ''
        label = '全部'
    }
    this.setData({
      'dateRange.start': start,
      'dateRange.end': end,
      dateLabel: label
    })
    this.loadData()
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadData().then(function() {
      wx.stopPullDownRefresh()
    }).catch(function() {
      wx.stopPullDownRefresh()
    })
  },

  // 点击明细项查看工单详情
  onItemTap(e) {
    const orderNo = e.currentTarget.dataset.order
    if (orderNo) {
      wx.navigateTo({ url: '/pages/work-order/detail/detail?order_no=' + orderNo })
    }
  },

  // 重新加载
  onReload() {
    this.loadData()
  }
})
