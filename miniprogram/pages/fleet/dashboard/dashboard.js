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
      const [fleetStats, fleetTodos, fleetVehicles] = await Promise.all([
        api.getFleetStats ? api.getFleetStats().catch(() => ({})) : Promise.resolve({}),
        api.getFleetTodos ? api.getFleetTodos().catch(() => ({})) : Promise.resolve({}),
        api.getFleetVehicles ? api.getFleetVehicles().catch(() => []) : Promise.resolve([])
      ])

      this.setData({
        stats: {
          totalVehicles: fleetStats.total_vehicles || fleetStats.total || 0,
          runningCount: fleetStats.running_count || fleetStats.running || 0,
          maintenanceCount: fleetStats.maintenance_count || fleetStats.maintenance || 0,
          monthlyExpense: fleetStats.monthly_expense || fleetStats.expense || 0
        },
        todos: {
          maintenanceDue: fleetTodos.maintenance_due || fleetTodos.maintenance || 0,
          inspectionDue: fleetTodos.inspection_due || fleetTodos.inspection || 0
        },
        vehicles: Array.isArray(fleetVehicles) ? fleetVehicles.map(this._formatVehicle.bind(this)) : [],
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
      _statusColor: info.color
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
