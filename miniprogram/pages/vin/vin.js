const api = require('../../utils/api')

const HISTORY_KEY = 'vin_decode_history'

Page({
  data: {
    vin: '',
    loading: false,
    searched: false,
    result: null,
    error: '',
    history: []
  },

  onLoad() {
    const history = wx.getStorageSync(HISTORY_KEY) || []
    this.setData({ history })
  },

  onUnload() {
    if (this.data.vin) {
      this._saveHistory(this.data.vin)
    }
  },

  onVinInput(e) {
    let val = (e.detail.value || '').toUpperCase().replace(/[^A-Z0-9]/g, '')
    this.setData({ vin: val })
  },

  async onDecode() {
    const vin = this.data.vin.trim()
    if (vin.length !== 17) {
      wx.showToast({ title: 'VIN码必须为17位', icon: 'none' })
      return
    }
    if (!/^[A-HJ-NPR-Z0-9]{17}$/.test(vin)) {
      wx.showToast({ title: 'VIN码包含非法字符', icon: 'none' })
      return
    }

    this.setData({ loading: true, searched: true, result: null, error: '' })

    try {
      const res = await api.decodeVin(vin)
      if (res && res.data) {
        this.setData({ result: res.data, error: '' })
      } else if (res) {
        this.setData({ result: res, error: '' })
      } else {
        this.setData({ result: null, error: '未找到该VIN对应的车型信息' })
      }
      this._saveHistory(vin)
    } catch (e) {
      this.setData({
        result: null,
        error: e.msg || e.message || '解码失败，请检查VIN码后重试'
      })
    }

    this.setData({ loading: false })
  },

  onHistoryTap(e) {
    const vin = e.currentTarget.dataset.vin
    this.setData({ vin })
    this.onDecode()
  },

  _saveHistory(vin) {
    let history = wx.getStorageSync(HISTORY_KEY) || []
    history = history.filter(function(v) { return v !== vin })
    history.unshift(vin)
    if (history.length > 20) {
      history = history.slice(0, 20)
    }
    wx.setStorageSync(HISTORY_KEY, history)
    this.setData({ history: history })
  }
})
