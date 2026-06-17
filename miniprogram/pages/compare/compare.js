const api = require('../../utils/api');

Page({
  data: {
    current: { period: '', revenue: 0, orders: 0, avg_ticket: 0 },
    previous: { period: '', revenue: 0, orders: 0, avg_ticket: 0 },
    changes: { revenue_percent: 0, orders_percent: 0, avg_ticket_percent: 0 },
    loading: false,
  },

  onLoad() {
    this.loadCompare();
  },

  onPullDownRefresh() {
    this.loadCompare().then(() => wx.stopPullDownRefresh());
  },

  loadCompare() {
    this.setData({ loading: true });
    const now = new Date();
    const start = '2026-01-01';
    const end = this._fmtDate(now);

    return api.request('/reports/compare', 'GET', { start, end }).then(function(data) {
        if (data && data.current) {
          this.setData({
            current: data.current,
            previous: data.previous,
            changes: data.changes,
          });
        }
        this.setData({ loading: false });
      }.bind(this), function() {
        wx.showToast({ title: '加载失败', icon: 'none' });
        this.setData({ loading: false });
      }.bind(this));
  },

  _fmtDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  },
});
