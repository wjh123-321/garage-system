// 技师绩效页面
const app = getApp()

// 模拟数据
const MOCK_TECHS = [
  { id: 1, name: '张伟', role: '高级技师',   avatar: '', orders: 42, revenue: 52600, prevOrders: 38, prevRevenue: 48000 },
  { id: 2, name: '李强', role: '中级技师',   avatar: '', orders: 38, revenue: 47300, prevOrders: 40, prevRevenue: 49500 },
  { id: 3, name: '王磊', role: '高级技师',   avatar: '', orders: 35, revenue: 51200, prevOrders: 32, prevRevenue: 46000 },
  { id: 4, name: '刘洋', role: '中级技师',   avatar: '', orders: 31, revenue: 38900, prevOrders: 30, prevRevenue: 37500 },
  { id: 5, name: '陈明', role: '初级技师',   avatar: '', orders: 28, revenue: 34200, prevOrders: 26, prevRevenue: 31000 },
  { id: 6, name: '赵刚', role: '中级技师',   avatar: '', orders: 25, revenue: 29800, prevOrders: 27, prevRevenue: 32000 },
  { id: 7, name: '孙杰', role: '初级技师',   avatar: '', orders: 22, revenue: 26500, prevOrders: 20, prevRevenue: 24000 },
  { id: 8, name: '周华', role: '初级技师',   avatar: '', orders: 18, revenue: 21300, prevOrders: 19, prevRevenue: 22500 },
]

Page({
  data: {
    totalTechs: 0,
    totalOrders: 0,
    totalRevenue: 0,
    techList: [],
    sortBy: 'orders',      // orders | revenue
    loading: false,
    hasMore: true,
    page: 1,
    pageSize: 20,
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    // 每次显示时刷新
    if (this.data.techList.length > 0) {
      this.loadData()
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadData(() => {
      wx.stopPullDownRefresh()
    })
  },

  // 加载数据
  loadData(callback) {
    this.setData({ loading: true })

    // 模拟 API 请求
    setTimeout(() => {
      const rawData = MOCK_TECHS.slice()
      let sorted = this.sortTechs(rawData, this.data.sortBy)

      // 计算排名变动（与上一期比较）
      sorted = sorted.map((item, index) => {
        const prevRank = this.calcPrevRank(sorted, item, this.data.sortBy)
        return {
          ...item,
          orders: item.orders,
          revenue: item.revenue.toLocaleString(),
          rankChange: prevRank === -1 ? 0 : prevRank - (index + 1),
        }
      })

      // 汇总统计
      const totalTechs = sorted.length
      const totalOrders = MOCK_TECHS.reduce((s, t) => s + t.orders, 0)
      const totalRevenue = MOCK_TECHS.reduce((s, t) => s + t.revenue, 0).toLocaleString()

      this.setData({
        totalTechs,
        totalOrders,
        totalRevenue,
        techList: sorted,
        loading: false,
        hasMore: false,
        page: 1,
      }, () => {
        callback && callback()
      })
    }, 300)
  },

  // 排序
  sortTechs(list, by) {
    const copy = [...list]
    if (by === 'orders') {
      copy.sort((a, b) => b.orders - a.orders)
    } else {
      copy.sort((a, b) => b.revenue - a.revenue)
    }
    return copy
  },

  // 计算上一期排名（基于历史数据）
  calcPrevRank(sorted, item, by) {
    const prevList = [...MOCK_TECHS].map(t => ({
      ...t,
      orders: t.prevOrders,
      revenue: t.prevRevenue,
    }))
    const sortedPrev = this.sortTechs(prevList, by)
    const idx = sortedPrev.findIndex(t => t.id === item.id)
    return idx === -1 ? -1 : idx + 1
  },

  // 切换排序方式
  onSortChange(e) {
    const sortBy = e.currentTarget.dataset.sort
    if (sortBy === this.data.sortBy) return

    this.setData({ sortBy, loading: true })

    setTimeout(() => {
      const rawData = MOCK_TECHS.slice()
      let sorted = this.sortTechs(rawData, sortBy)
      sorted = sorted.map((item, index) => {
        const prevRank = this.calcPrevRank(sorted, item, sortBy)
        return {
          ...item,
          orders: item.orders,
          revenue: item.revenue.toLocaleString(),
          rankChange: prevRank === -1 ? 0 : prevRank - (index + 1),
        }
      })
      this.setData({
        techList: sorted,
        loading: false,
      })
    }, 200)
  },

  // 加载更多（预留分页）
  onLoadMore() {
    if (this.data.loading || !this.data.hasMore) return
    // 实际项目中从后端分页拉取
  },
})
