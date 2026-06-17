const api = require('../../utils/api')

Page({
  data: {
    year: 0,
    month: 0,
    selectedDate: '',
    selectedLabel: '',
    weekdays: ['日', '一', '二', '三', '四', '五', '六'],
    calendarDays: [],
    appointments: [],
    loading: false,
    // 存储各日期是否有预约，用于标记圆点
    _appointmentMap: {}
  },

  onLoad() {
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth() + 1
    const todayStr = this._fmtDate(now)
    this.setData({ year, month, selectedDate: todayStr, selectedLabel: todayStr })
    this._buildCalendar(year, month)
    this._loadAppointments(todayStr)
  },

  // ---------- 日历构建 ----------

  _buildCalendar(year, month) {
    const firstDay = new Date(year, month - 1, 1).getDay() // 0=日
    const daysInMonth = new Date(year, month, 0).getDate()
    const daysInPrev = new Date(year, month - 1, 0).getDate()
    const today = new Date()
    const todayStr = this._fmtDate(today)

    // 上个月补齐
    const days = []
    for (let i = firstDay - 1; i >= 0; i--) {
      const d = daysInPrev - i
      const dateStr = this._fmtDate(new Date(year, month - 2, d))
      days.push({ dayNum: d, dateStr, isCurrentMonth: false, isToday: false, isSelected: dateStr === this.data.selectedDate, isEmpty: false })
    }
    // 本月
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = this._fmtDate(new Date(year, month - 1, d))
      const isToday = dateStr === todayStr
      days.push({ dayNum: d, dateStr, isCurrentMonth: true, isToday, isSelected: dateStr === this.data.selectedDate, isEmpty: false })
    }
    // 下个月补齐 6行=42格
    const remaining = 42 - days.length
    for (let d = 1; d <= remaining; d++) {
      const dateStr = this._fmtDate(new Date(year, month, d))
      days.push({ dayNum: d, dateStr, isCurrentMonth: false, isToday: false, isSelected: dateStr === this.data.selectedDate, isEmpty: false })
    }

    // 标记有预约的日期
    const map = this.data._appointmentMap || {}
    for (const day of days) {
      day.hasAppointment = !!map[day.dateStr]
    }

    this.setData({ calendarDays: days })
  },

  // ---------- 月份切换 ----------

  prevMonth() {
    let { year, month } = this.data
    month--
    if (month < 1) { month = 12; year-- }
    this.setData({ year, month })
    this._buildCalendar(year, month)
    // 选中当月1号
    const firstDate = this._fmtDate(new Date(year, month - 1, 1))
    this._selectDate(firstDate)
  },

  nextMonth() {
    let { year, month } = this.data
    month++
    if (month > 12) { month = 1; year++ }
    this.setData({ year, month })
    this._buildCalendar(year, month)
    const firstDate = this._fmtDate(new Date(year, month - 1, 1))
    this._selectDate(firstDate)
  },

  // ---------- 日期选择 ----------

  selectDay(e) {
    const dateStr = e.currentTarget.dataset.date
    const empty = e.currentTarget.dataset.empty
    if (empty) return
    this._selectDate(dateStr)
  },

  _selectDate(dateStr) {
    this.setData({ selectedDate: dateStr, selectedLabel: dateStr })
    // 重绘日历高亮
    const days = this.data.calendarDays.map(d => ({ ...d, isSelected: d.dateStr === dateStr }))
    this.setData({ calendarDays: days })
    this._loadAppointments(dateStr)
  },

  // ---------- 数据加载 ----------

  async _loadAppointments(dateStr) {
    this.setData({ loading: true })
    try {
      const list = await api.getAppointmentsByDate(dateStr)
      this.setData({ appointments: list, loading: false })

      // 更新预约标记映射
      const map = this.data._appointmentMap || {}
      // 只保留当前可见月份的key（简单起见，累加也行）
      const visibleDates = this.data.calendarDays.map(d => d.dateStr)
      // 合并已有标记（不清除其他月份已加载的）
      for (const a of list) {
        if (a.appoint_date) map[a.appoint_date] = true
      }
      this.setData({ _appointmentMap: map })

      // 刷新日历中的圆点
      const days = this.data.calendarDays.map(d => ({
        ...d,
        hasAppointment: !!map[d.dateStr]
      }))
      this.setData({ calendarDays: days })
    } catch (e) {
      console.warn('加载预约失败', e)
      this.setData({ loading: false })
    }
  },

  // ---------- 跳转详情 (预留) ----------

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: '预约ID: ' + id, icon: 'none' })
  },

  // ---------- 工具 ----------

  _fmtDate(d) {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return y + '-' + m + '-' + day
  }
})
