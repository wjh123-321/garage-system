const api = require('../../../utils/api')

Page({
  data: {
    customer: null,
    orders: [],
    isNew: false,
    loading: false,
    aiAnalysis: null,
    aiLoading: false,
    form: { name: '', phone: '', car_plate: '', car_model: '', vin: '', mileage: '' }
  },
  onLoad(options) {
    if (options.id) {
      this.loadCustomer(options.id)
    } else {
      this.setData({ isNew: true })
    }
  },
  async loadCustomer(id) {
    this.setData({ loading: true })
    try {
      const res = await api.getCustomer(id)
      const c = res.data || res
      this.setData({
        customer: c,
        form: { name: c.name || '', phone: c.phone || '', car_plate: c.car_plate || '',
                car_model: c.car_model || '', vin: c.vin || '', mileage: c.mileage || '' }
      })
      this.loadAIAnalysis(id)
    } catch(e) { wx.showToast({ title: '加载失败', icon: 'none' }) }
    this.setData({ loading: false })
  },
  async loadAIAnalysis(customerId) {
    this.setData({ aiLoading: true })
    try {
      var res = await api.getAICustomerAnalysis(customerId)
      var ai = res.data || res
      if (ai && ai.customer_tier) {
        ai._churnDisplay = ai.churn_risk === 'high' ? '⚠️ 高' : ai.churn_risk === 'medium' ? '⚡ 中' : '✅ 低'
        ai._totalVisits = ai.total_visits || 0
        ai._avgTicket = Math.round(ai.avg_ticket || 0)
        ai._visitFreq = ai.visit_frequency_days || '-'
        this.setData({ aiAnalysis: ai, aiLoading: false })
      } else { this.setData({ aiLoading: false }) }
    } catch(e) { this.setData({ aiLoading: false }) }
  },
  onNameInput(e) {
    this.setData({ form: { ...this.data.form, name: e.detail.value } })
  },
  onPhoneInput(e) {
    this.setData({ form: { ...this.data.form, phone: e.detail.value } })
  },
  onPlateInput(e) {
    this.setData({ form: { ...this.data.form, car_plate: e.detail.value } })
  },
  onModelInput(e) {
    this.setData({ form: { ...this.data.form, car_model: e.detail.value } })
  },
  submit() {
    const f = this.data.form
    if (!f.name) { wx.showToast({ title: '请填写姓名', icon: 'none' }); return }
    var data = {
      name: f.name,
      phone: f.phone,
      car_plate: f.car_plate,
      car_model: f.car_model,
      vin: f.vin,
      mileage: parseInt(f.mileage) || 0,
      is_active: true
    }
    if (this.data.isNew) {
      api.createCustomer(data).then(function() {
        wx.showToast({ title: '创建成功', icon: 'success' })
        setTimeout(function() { wx.navigateBack() }, 1500)
      }).catch(function() {
        wx.showToast({ title: '保存失败', icon: 'none' })
      })
    } else {
      api.request('/customers/' + this.data.customer.id, 'PUT', data).then(function() {
        wx.showToast({ title: '保存成功', icon: 'success' })
        setTimeout(function() { wx.navigateBack() }, 1500)
      }).catch(function() {
        wx.showToast({ title: '保存失败', icon: 'none' })
      })
    }
  }
})
