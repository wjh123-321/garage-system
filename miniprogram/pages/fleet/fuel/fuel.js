const api = require('../../../utils/api')
const { formatDate } = require('../../../utils/util')

Page({
  data: {
    // 车辆选择
    vehicleList: [
      { id: 1, name: '京A·88888' },
      { id: 2, name: '京B·66666' }
    ],
    currentVehicleId: 1,
    vehicleName: '京A·88888',

    // 汇总
    summary: {
      totalMileage: '0',
      totalCost: '¥0',
      avgConsumption: '0.0'
    },

    // 表单
    formVisible: false,
    form: {
      date: formatDate(new Date()),
      mileage: '',
      liters: '',
      amount: '',
      station: ''
    },

    // 记录列表
    records: [],
    loading: true
  },

  onLoad() {
    this.loadRecords()
  },

  onPullDownRefresh() {
    this.loadRecords(() => {
      wx.stopPullDownRefresh()
    })
  },

  // ===== 数据加载 =====
  async loadRecords(callback) {
    this.setData({ loading: true })
    try {
      // 优先从 API 获取
      const res = await api.request({
        url: '/api/fleet/fuel-records',
        data: { vehicle_id: this.data.currentVehicleId },
        failSilently: true
      })

      if (res && res.code === 0 && Array.isArray(res.data)) {
        this.setData({ records: res.data })
      } else {
        // 用模拟数据兜底
        this.setData({ records: this._mockRecords() })
      }

      this._calcSummary()
    } catch (e) {
      this.setData({ records: this._mockRecords() })
      this._calcSummary()
    } finally {
      this.setData({ loading: false })
      if (typeof callback === 'function') callback()
    }
  },

  // ===== 车辆切换 =====
  pickVehicle() {
    const list = this.data.vehicleList
    const current = this.data.currentVehicleId
    const items = list.map(v => v.name)
    const currentIndex = list.findIndex(v => v.id === current)

    wx.showActionSheet({
      itemList: items,
      success: (res) => {
        const selected = list[res.tapIndex]
        this.setData({
          currentVehicleId: selected.id,
          vehicleName: selected.name,
          loading: true
        })
        this.loadRecords()
      }
    })
  },

  // ===== 表单 =====
  showAddForm() {
    this.setData({
      formVisible: true,
      form: {
        date: formatDate(new Date()),
        mileage: '',
        liters: '',
        amount: '',
        station: ''
      }
    })
  },

  hideAddForm() {
    this.setData({ formVisible: false })
  },

  onDateChange(e) {
    this.setData({
      'form.date': e.detail.value
    })
  },

  onFieldInput(e) {
    const field = e.currentTarget.dataset.field
    const value = e.detail.value
    this.setData({
      ['form.' + field]: value
    })
  },

  submitRecord() {
    const form = this.data.form

    // 校验
    if (!form.mileage) {
      wx.showToast({ title: '请输入里程', icon: 'none' })
      return
    }
    if (!form.liters) {
      wx.showToast({ title: '请输入加油量', icon: 'none' })
      return
    }
    if (!form.amount) {
      wx.showToast({ title: '请输入金额', icon: 'none' })
      return
    }

    const mileageNum = parseFloat(form.mileage)
    const litersNum = parseFloat(form.liters)
    const amountNum = parseFloat(form.amount)

    if (isNaN(mileageNum) || mileageNum <= 0) {
      wx.showToast({ title: '里程格式有误', icon: 'none' })
      return
    }
    if (isNaN(litersNum) || litersNum <= 0) {
      wx.showToast({ title: '油量格式有误', icon: 'none' })
      return
    }
    if (isNaN(amountNum) || amountNum <= 0) {
      wx.showToast({ title: '金额格式有误', icon: 'none' })
      return
    }

    const newRecord = {
      id: Date.now().toString(),
      date: form.date,
      mileage: mileageNum,
      liters: litersNum.toFixed(1),
      amount: amountNum.toFixed(2),
      station: form.station || '',
      vehicle_id: this.data.currentVehicleId
    }

    // 提交到服务端
    this._submitToServer(newRecord)

    // 本地插入并刷新
    const records = [newRecord, ...this.data.records]
    this.setData({ records, formVisible: false })
    this._calcSummary()

    wx.showToast({ title: '保存成功', icon: 'success' })
  },

  async _submitToServer(record) {
    try {
      await api.request({
        url: '/api/fleet/fuel-records',
        method: 'POST',
        data: record,
        failSilently: true
      })
    } catch (e) {
      // 静默失败，本地已插入
    }
  },

  // ===== 汇总计算 =====
  _calcSummary() {
    const records = this.data.records
    if (!records || records.length === 0) {
      this.setData({
        summary: {
          totalMileage: '0',
          totalCost: '¥0',
          avgConsumption: '0.0'
        }
      })
      return
    }

    // 总里程 = 最新里程 - 最早里程
    const sorted = [...records].sort((a, b) => a.mileage - b.mileage)
    const firstMileage = parseFloat(sorted[0].mileage) || 0
    const lastMileage = parseFloat(sorted[sorted.length - 1].mileage) || 0
    const totalMileage = Math.max(0, lastMileage - firstMileage)

    // 总油费
    let totalCost = 0
    let totalLiters = 0
    records.forEach(r => {
      totalCost += parseFloat(r.amount) || 0
      totalLiters += parseFloat(r.liters) || 0
    })

    // 平均油耗 (L/100km)
    let avgConsumption = 0
    if (totalMileage > 0) {
      avgConsumption = (totalLiters / totalMileage * 100)
    }

    this.setData({
      summary: {
        totalMileage: totalMileage.toLocaleString(),
        totalCost: '¥' + totalCost.toFixed(2),
        avgConsumption: avgConsumption.toFixed(1)
      }
    })
  },

  // ===== 模拟数据 =====
  _mockRecords() {
    return [
      { id: '1', date: '2026-06-15', mileage: 12450, liters: '48.5', amount: '387.02', station: '中石化清华站' },
      { id: '2', date: '2026-06-08', mileage: 12020, liters: '45.0', amount: '355.50', station: '中石油北苑站' },
      { id: '3', date: '2026-05-28', mileage: 11580, liters: '50.2', amount: '411.64', station: '壳牌来广营' },
      { id: '4', date: '2026-05-15', mileage: 11150, liters: '47.8', amount: '377.62', station: '中石化清华站' },
      { id: '5', date: '2026-05-02', mileage: 10700, liters: '52.0', amount: '426.40', station: '中石油天通苑' }
    ]
  }
})
