const api = require('../../../utils/api')

Page({
  data: {
    // 统计卡片
    stats: {
      totalVehicles: 0,
      runningCount: 0,
      maintenanceCount: 0,
      monthlyExpense: 0
    },
    // 待办事项
    todos: {
      maintenanceDue: 0,
      inspectionDue: 0
    },
    // 车辆状态列表
    vehicles: [],
    loading: true
  },

  onShow() {
    this.loadData()
  },

  async loadData() {
    this.setData({ loading: true })
    try {
      const dashData = await api.getFleetDashboard().catch(function() { return {} })
      const vehData = await api.getFleetVehicles().catch(function() { return [] })

      this.setData({
        stats: {
          totalVehicles: dashData.total_vehicles || dashData.total || 0,
          runningCount: dashData.running || dashData.active || 0,
          maintenanceCount: dashData.maintenance || 0,
          monthlyExpense: dashData.month_expense || dashData.monthly_expense || 0,
          _monthlyExpenseDisplay: (dashData.month_expense || 0).toLocaleString()
        },
        todos: {
          maintenanceDue: dashData.due_maintenance || 0,
          inspectionDue: dashData.due_inspection || 0
        },
        vehicles: Array.isArray(vehData) ? vehData.map(this._formatVehicle.bind(this)) : [],
        loading: false
      })
    } catch (e) {
      this.setData({ loading: false })
    }
  },

  _formatVehicle(vehicle) {
    var status = (vehicle.status || 'stopped').toLowerCase()
    var statusMap = {
      running: { label: '运行中', className: 'running', color: '#2e7d32' },
      maintenance: { label: '维修中', className: 'maintenance', color: '#e65100' },
      stopped: { label: '停运', className: 'stopped', color: '#9e9e9e' }
    }
    var info = statusMap[status] || statusMap.stopped
    return {
      id: vehicle.id,
      plate: vehicle.plate || vehicle.car_plate || '--',
      brand: vehicle.brand || vehicle.model || '--',
      driver: vehicle.driver || vehicle.driver_name || '--',
      mileage: vehicle.mileage || 0,
      status: status,
      _statusLabel: info.label,
      _statusClass: info.className,
      _statusColor: info.color,
      _mileageDisplay: vehicle.mileage < 10000 ? vehicle.mileage + ' km' : (vehicle.mileage / 10000).toFixed(1) + ' 万 km'
    }
  },

  goVehicleDetail(e) {
    var id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/fleet/vehicle/detail/detail?id=' + id })
  },

  goTodo(e) {
    var type = e.currentTarget.dataset.type
    var url = type === 'maintenance'
      ? '/pages/fleet/maintenance/list/list'
      : '/pages/fleet/inspection/list/list'
    wx.navigateTo({ url: url })
  },

  goExpense() {
    wx.navigateTo({ url: '/pages/finance/finance?type=fleet' })
  }
})
