const api = require('../../utils/api')
const { formatTime } = require('../../utils/util')

Page({
  data: {
    notifications: [],
    page: 1,
    hasMore: true,
    loading: false,
    _showEmpty: false
  },

  onLoad() {
    this.loadNotifications(true)
  },

  onPullDownRefresh() {
    this.loadNotifications(true).then(function() { wx.stopPullDownRefresh() })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadNotifications()
    }
  },

  _computeDisplay(item) {
    var typeMap = {
      'maintenance': { icon: '🔧', label: '保养提醒' },
      'inspection': { icon: '📋', label: '年检提醒' },
      'pickup': { icon: '🚗', label: '取车提醒' },
      'renewal': { icon: '📄', label: '续保提醒' }
    }
    var t = typeMap[item.type] || { icon: '📩', label: item.type || '通知' }
    return {
      _typeIcon: t.icon,
      _typeLabel: t.label,
      _time: formatTime(item.created_at),
      _statusLabel: item.status === 'sent' ? '已发送' : '待发送',
      _statusClass: item.status === 'sent' ? 'sent' : 'pending'
    }
  },

  async loadNotifications(refresh) {
    if (refresh === undefined) refresh = false
    if (this.data.loading) return
    this.setData({ loading: true })
    if (refresh) this.setData({ page: 1, notifications: [] })
    try {
      const params = { page: this.data.page, page_size: 20 }
      const res = await api.get('/api/notifications', { data: params }) || {}
      const items = res.items || res.data || []
      var computedItems = items.map(this._computeDisplay.bind(this))
      this.setData({
        notifications: refresh ? computedItems : [...this.data.notifications, ...computedItems],
        hasMore: items.length >= 20,
        page: this.data.page + 1,
        _showEmpty: computedItems.length === 0,
        loading: false
      })
    } catch(e) {
      this.setData({ loading: false })
      if (refresh && this.data.notifications.length === 0) {
        this._loadMockData()
      }
    }
  },

  _loadMockData() {
    var now = Date.now()
    var mockItems = [
      { id: 1, customer_name: '张先生', car_plate: '京A·88888', type: 'maintenance', message: '您的爱车已到保养周期，请尽快到店保养。', created_at: now - 86400000, status: 'pending' },
      { id: 2, customer_name: '李女士', car_plate: '沪B·66666', type: 'inspection', message: '您的车辆年检即将到期，请安排时间到店检测。', created_at: now - 172800000, status: 'pending' },
      { id: 3, customer_name: '王先生', car_plate: '粤C·12345', type: 'pickup', message: '您的车辆已完成维修，可随时到店取车。', created_at: now - 259200000, status: 'pending' },
      { id: 4, customer_name: '赵先生', car_plate: '苏D·99999', type: 'maintenance', message: '距上次保养已行驶5000公里，建议回店检查。', created_at: now - 345600000, status: 'sent' },
      { id: 5, customer_name: '刘女士', car_plate: '浙E·77777', type: 'renewal', message: '您的车险将于15天后到期，请及时续保。', created_at: now - 432000000, status: 'pending' }
    ]
    var computed = mockItems.map(this._computeDisplay.bind(this))
    this.setData({
      notifications: computed,
      hasMore: false,
      _showEmpty: false,
      loading: false
    })
  },

  markAsSent(e) {
    var id = e.currentTarget.dataset.id
    var list = this.data.notifications
    var idx = list.findIndex(function(n) { return n.id === id })
    if (idx === -1 || list[idx].status === 'sent') return

    wx.showModal({
      title: '确认发送',
      content: '标记该提醒为已发送？',
      success: function(res) {
        if (!res.confirm) return
        // optimistic update
        var updated = 'notifications[' + idx + '].status'
        var statusLabel = 'notifications[' + idx + ']._statusLabel'
        var statusClass = 'notifications[' + idx + ']._statusClass'
        this.setData({
          [updated]: 'sent',
          [statusLabel]: '已发送',
          [statusClass]: 'sent'
        })
        // sync to server
        api.post('/api/notifications/' + id + '/send').catch(function() {
          // rollback on failure
          var rollback = 'notifications[' + idx + '].status'
          var rbLabel = 'notifications[' + idx + ']._statusLabel'
          var rbClass = 'notifications[' + idx + ']._statusClass'
          this.setData({
            [rollback]: 'pending',
            [rbLabel]: '待发送',
            [rbClass]: 'pending'
          })
          wx.showToast({ title: '同步失败', icon: 'none' })
        }.bind(this))
        wx.showToast({ title: '已标记发送', icon: 'success' })
      }.bind(this)
    })
  },

  sendAll() {
    var pending = this.data.notifications.filter(function(n) { return n.status === 'pending' })
    if (pending.length === 0) {
      wx.showToast({ title: '没有待发送的提醒', icon: 'none' })
      return
    }
    wx.showModal({
      title: '批量发送',
      content: '确定发送全部 ' + pending.length + ' 条待发送提醒？',
      success: function(res) {
        if (!res.confirm) return
        pending.forEach(function(n) {
          api.post('/api/notifications/' + n.id + '/send').catch(function() {})
        })
        this._refreshAllStatus()
        wx.showToast({ title: '已全部标记发送', icon: 'success' })
      }.bind(this)
    })
  },

  _refreshAllStatus() {
    var list = this.data.notifications
    var data = {}
    for (var i = 0; i < list.length; i++) {
      data['notifications[' + i + '].status'] = 'sent'
      data['notifications[' + i + ']._statusLabel'] = '已发送'
      data['notifications[' + i + ']._statusClass'] = 'sent'
    }
    this.setData(data)
  }
})
