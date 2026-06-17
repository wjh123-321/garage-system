const app = getApp();

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

    return wx.request({
      url: `${app.globalData.baseUrl}/reports/compare`,
      data: { start, end },
      success: (res) => {
        if (res.data && res.data.current) {
          this.setData({
            current: res.data.current,
            previous: res.data.previous,
            changes: res.data.changes,
          });
        }
      },
      fail: () => {
        wx.showToast({ title: '加载失败', icon: 'none' });
      },
      complete: () => {
        this.setData({ loading: false });
      },
    });
  },

  _fmtDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  },
});
