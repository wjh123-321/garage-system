const app = getApp()

// 车辆状态枚举
const VEHICLE_STATUS = {
  ACTIVE: { label: '运营中', value: 'active', color: '#07c160' },
  MAINTENANCE: { label: '维修中', value: 'maintenance', color: '#fa9a3e' },
  IDLE: { label: '闲置', value: 'idle', color: '#888' },
  RETIRED: { label: '已报废', value: 'retired', color: '#c0c0c0' },
}

// ---- Mock 数据 ----
const mockVehicles = [
  {
    id: 'V001',
    plate: '京A·88888',
    brand: '丰田',
    model: '凯美瑞 2024款 双擎 2.5HGVP',
    year: 2024,
    vin: 'LVGBH42K8RG123456',
    driver: '张伟',
    driverPhone: '13800138001',
    status: 'active',
    insuranceExpiry: '2026-12-31',
    inspectionExpiry: '2027-03-15',
    purchaseDate: '2024-06-01',
    mileage: 35800,
    monthlyIncome: 28500,
    monthlyFuel: 6200,
    monthlyMaintenance: 1800,
  },
  {
    id: 'V002',
    plate: '京B·66666',
    brand: '大众',
    model: '帕萨特 2023款 330TSI 豪华版',
    year: 2023,
    vin: 'LSVCD6C46PN123789',
    driver: '李明',
    driverPhone: '13900139002',
    status: 'active',
    insuranceExpiry: '2026-08-20',
    inspectionExpiry: '2026-08-20',
    purchaseDate: '2023-05-20',
    mileage: 51200,
    monthlyIncome: 31200,
    monthlyFuel: 7800,
    monthlyMaintenance: 2100,
  },
  {
    id: 'V003',
    plate: '京C·12345',
    brand: '本田',
    model: '雅阁 2023款 260TURBO 幻夜·旗舰版',
    year: 2023,
    vin: 'LHGCR6686P8004567',
    driver: '王强',
    driverPhone: '13700137003',
    status: 'maintenance',
    insuranceExpiry: '2026-03-10',
    inspectionExpiry: '2026-03-10',
    purchaseDate: '2023-03-10',
    mileage: 48900,
    monthlyIncome: 26800,
    monthlyFuel: 6500,
    monthlyMaintenance: 4500,
  },
  {
    id: 'V004',
    plate: '京D·99999',
    brand: '比亚迪',
    model: '汉 EV 2024款 四驱旗舰型',
    year: 2024,
    vin: 'LC0CE6CB7R1012345',
    driver: '赵刚',
    driverPhone: '13600136004',
    status: 'active',
    insuranceExpiry: '2027-01-20',
    inspectionExpiry: '2027-01-20',
    purchaseDate: '2024-01-20',
    mileage: 22600,
    monthlyIncome: 35600,
    monthlyFuel: 2100,
    monthlyMaintenance: 900,
  },
  {
    id: 'V005',
    plate: '京E·77777',
    brand: '五菱',
    model: '宏光PLUS 1.5T 舒适型',
    year: 2022,
    vin: 'LZWADAGA5NB678901',
    driver: '刘洋',
    driverPhone: '13500135005',
    status: 'idle',
    insuranceExpiry: '2026-05-08',
    inspectionExpiry: '2026-05-08',
    purchaseDate: '2022-05-08',
    mileage: 80400,
    monthlyIncome: 0,
    monthlyFuel: 0,
    monthlyMaintenance: 0,
  },
]

Page({
  data: {
    // 视图控制: 'list' | 'detail' | 'add'
    view: 'list',
    // 列表
    vehicles: [],
    statusFilter: '',
    searchKeyword: '',
    statusOptions: Object.values(VEHICLE_STATUS),
    // 详情
    currentVehicle: null,
    activeTab: 0,
    tabs: [
      { id: 'archive', label: '车辆档案' },
      { id: 'maintenance', label: '维修记录' },
      { id: 'fuel', label: '油耗记录' },
      { id: 'finance', label: '收支' },
    ],
    // 添加表单
    formData: {
      plate: '',
      brand: '',
      model: '',
      year: '',
      vin: '',
      driver: '',
      driverPhone: '',
      purchaseDate: '',
      insuranceExpiry: '',
      inspectionExpiry: '',
    },
    // 维修记录（mock）
    maintenanceRecords: [],
    // 油耗记录（mock）
    fuelRecords: [],
    // 收支记录（mock）
    financeRecords: [],
  },

  onLoad() {
    this.loadVehicles()
    this.loadMockRecords()
  },

  onPullDownRefresh() {
    this.loadVehicles()
    wx.stopPullDownRefresh()
  },

  // ==================== 数据加载 ====================

  loadVehicles() {
    let list = [...mockVehicles]
    const { statusFilter, searchKeyword } = this.data

    if (statusFilter) {
      list = list.filter(v => v.status === statusFilter)
    }
    if (searchKeyword) {
      const kw = searchKeyword.toLowerCase()
      list = list.filter(v =>
        v.plate.toLowerCase().includes(kw) ||
        v.brand.includes(kw) ||
        v.driver.includes(kw) ||
        v.model.includes(kw)
      )
    }

    this.setData({ vehicles: list.map(this._enrichVehicle.bind(this)) })
  },

  _enrichVehicle(v) {
    var statusInfo = this.getStatusInfo(v.status)
    return {
      ...v,
      _statusLabel: statusInfo.label,
      _statusClass: statusInfo.value,
      _vinDisplay: v.vin ? v.vin.slice(-6) : '--',
      _insuranceWarning: this._isExpiring(v.insuranceExpiry),
      _inspectionWarning: this._isExpiring(v.inspectionExpiry),
    }
  },

  _isExpiring(dateStr) {
    if (!dateStr) return false
    var now = new Date()
    var expiry = new Date(dateStr)
    var diffMs = expiry.getTime() - now.getTime()
    var diffDays = diffMs / (1000 * 60 * 60 * 24)
    return diffDays >= 0 && diffDays <= 45
  },

  loadMockRecords() {
    // 维修记录
    this.setData({
      maintenanceRecords: [
        { id: 'M001', date: '2026-05-12', type: '保养', desc: '更换机油、机滤、空滤', cost: 680, shop: '金驰汽修' },
        { id: 'M002', date: '2026-03-20', type: '维修', desc: '右前轮轮胎更换', cost: 850, shop: '米其林驰加' },
        { id: 'M003', date: '2026-01-05', type: '保养', desc: '大保养 - 全车油液更换', cost: 3200, shop: '4S店' },
      ],
      fuelRecords: [
        { date: '2026-06-15', amount: '45.2L', cost: 372, mileage: 580, unitCost: 0.64 },
        { date: '2026-06-08', amount: '42.8L', cost: 351, mileage: 550, unitCost: 0.64 },
        { date: '2026-05-30', amount: '48.0L', cost: 394, mileage: 620, unitCost: 0.63 },
      ],
      financeRecords: [
        { date: '2026-06-15', type: 'income', category: '流水', amount: 1280, note: '6月15日流水' },
        { date: '2026-06-15', type: 'expense', category: '加油', amount: 372, note: '中石油' },
        { date: '2026-06-14', type: 'income', category: '流水', amount: 960, note: '6月14日流水' },
        { date: '2026-06-13', type: 'expense', category: '保养', amount: 680, note: '机油更换' },
      ],
    })
  },

  // ==================== 列表操作 ====================

  onSearchInput(e) {
    this.setData({ searchKeyword: e.detail.value }, () => this.loadVehicles())
  },

  onFilterChange(e) {
    this.setData({ statusFilter: e.currentTarget.dataset.value }, () => this.loadVehicles())
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id
    const vehicle = mockVehicles.find(v => v.id === id) || null
    if (vehicle) {
      this.setData({
        view: 'detail',
        currentVehicle: this._enrichVehicle(vehicle),
        activeTab: 0,
      })
    }
  },

  // ==================== 详情操作 ====================

  switchTab(e) {
    const index = e.currentTarget.dataset.index
    this.setData({ activeTab: parseInt(index, 10) })
  },

  goBack() {
    this.setData({ view: 'list', currentVehicle: null })
  },

  // ==================== 添加车辆 ====================

  showAddForm() {
    this.setData({
      view: 'add',
      formData: {
        plate: '', brand: '', model: '', year: '',
        vin: '', driver: '', driverPhone: '',
        purchaseDate: '', insuranceExpiry: '', inspectionExpiry: '',
      },
    })
  },

  onFormInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({
      [`formData.${field}`]: e.detail.value,
    })
  },

  submitVehicle() {
    const { formData } = this.data
    // 简单校验
    if (!formData.plate || !formData.brand || !formData.driver) {
      wx.showToast({ title: '请填写必要信息', icon: 'none' })
      return
    }
    // 生产环境调用 API，此处 mock
    wx.showLoading({ title: '提交中...' })
    setTimeout(() => {
      wx.hideLoading()
      wx.showToast({ title: '添加成功' })
      this.setData({ view: 'list' })
      // 实际应重新拉取列表
    }, 800)
  },

  // ==================== 工具函数 ====================

  getStatusInfo(status) {
    return VEHICLE_STATUS[status] || VEHICLE_STATUS.IDLE
  },

})
