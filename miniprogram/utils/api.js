const app = getApp()

const request = (url, method = 'GET', data = {}) => {
  return new Promise((resolve, reject) => {
    const baseUrl = app.globalData.baseUrl
    wx.request({
      url: `${baseUrl}${url}`,
      method,
      data,
      header: { 'Content-Type': 'application/json' },
      success: res => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          wx.showToast({ title: '请求失败', icon: 'none' })
          reject(res.data)
        }
      },
      fail: err => {
        wx.showToast({ title: '网络错误', icon: 'none' })
        reject(err)
      }
    })
  })
}

module.exports = {
  // 通用请求
  request: request,

  // 客户
  getCustomers: (params) => request('/customers?' + obj2Params(params)),
  getCustomer: (id) => request(`/customers/${id}`),
  createCustomer: (data) => request('/customers', 'POST', data),

  // 供应商
  getSuppliers: (params) => request('/suppliers?' + obj2Params(params)),
  getSupplier: (id) => request(`/suppliers/${id}`),
  createSupplier: (data) => request('/suppliers', 'POST', data),
  updateSupplier: (id, data) => request(`/suppliers/${id}`, 'PUT', data),

  // 工单
  getWorkOrders: (params) => request('/work-orders?' + obj2Params(params)),
  getWorkOrder: (id) => request(`/work-orders/${id}`),
  createWorkOrder: (data) => request('/work-orders', 'POST', data),
  updateWorkOrder: (id, data) => request(`/work-orders/${id}`, 'PUT', data),
  getByPlate: (plate) => request(`/work-orders/plate/${plate}`),
  decodeVin: (vin) => request("/vin/decode/" + vin),

  // 配件
  getParts: (params) => request('/parts?' + obj2Params(params)),
  getPart: (id) => request(`/parts/${id}`),
  getLowStock: () => request('/parts/low-stock'),

  // 提醒
  getReminders: (params) => request('/reminders?' + obj2Params(params)),

  // 预约
  getAppointmentsByDate: (date) => request('/appointments/date/' + date),

  // 统计
  getStats: () => request('/stats'),

  // AI智能引擎
  getAIRepairRecommend: (workOrderId) => request("/ai/repair/recommend", "POST", { work_order_id: workOrderId }),
  getAIPartsForecast: (params) => request("/ai/parts/forecast?days=" + ((params && params.horizon_months) ? params.horizon_months * 30 : 30)),
  getAICustomerAnalysis: (customerId) => request("/ai/customers/" + customerId + "/maintenance"),
  getAIDashboard: () => request("/ai/dashboard"),
  postAIFeedback: (recId, rating) => request("/ai/feedback", "POST", { recommendation_id: recId, feedback: rating >= 4 ? "accept" : "reject" }),
  getAICustomerSegments: () => request("/ai/customers/at-risk"),

  // 客户评价
  getReviews: (orderId) => request('/reviews?order_id=' + orderId),
  createReview: (data) => request('/reviews', 'POST', data),

  // 会员卡/次卡
  getMemberships: (params) => request('/memberships?' + obj2Params(params)),
  getMembership: (id) => request(`/memberships/${id}`),
  createMembership: (data) => request('/memberships', 'POST', data),
  updateMembership: (id, data) => request(`/memberships/${id}`, 'PUT', data),
  deleteMembership: (id) => request(`/memberships/${id}`, 'DELETE'),
  consumeMembership: (id, amount) => request(`/memberships/${id}/consume`, 'POST', { amount }),
  rechargeMembership: (id, amount) => request(`/memberships/${id}/recharge`, 'POST', { amount }),

  // 电子报价单
  getQuotation: (id) => request(`/quotations/${id}`),
  createQuotation: (data) => request('/quotations', 'POST', data),
  listQuotations: () => request('/quotations'),

  // 员工
  getStaffs: (params) => request('/staff?' + obj2Params(params)),
  getStaff: (id) => request(`/staff/${id}`),
  createStaff: (data) => request('/staff', 'POST', data),
  updateStaff: (id, data) => request(`/staff/${id}`, 'PUT', data),
  deleteStaff: (id) => request(`/staff/${id}`, 'DELETE'),

  // 验车单
  getInspection: (orderId) => request(`/inspection/${orderId}`),
  createInspection: (data) => request('/inspection', 'POST', data),
  updateInspection: (id, data) => request(`/inspection/${id}`, 'PUT', data),

  // 维修模板
  getTemplates: (params) => request('/templates?' + obj2Params(params)),
  getTemplate: (id) => request(`/templates/${id}`),
  getTemplateCategories: () => request('/templates/categories'),
  createTemplate: (data) => request('/templates', 'POST', data),
  updateTemplate: (id, data) => request(`/templates/${id}`, 'PUT', data),
  deleteTemplate: (id) => request(`/templates/${id}`, 'DELETE'),

  // 配件商城
  getPartsStoreBrands: () => request('/parts-store/brands'),
  getPartsStoreModels: (brand) => request('/parts-store/models?brand=' + encodeURIComponent(brand)),
  searchPartsStore: (params) => request('/parts-store/search?' + obj2Params(params)),
  getPartDetail: (params) => request('/parts-store/detail?' + obj2Params(params)),
  getPartsByVin: (vin) => request('/parts-store/vin/' + vin),
}

function obj2Params(obj) {
  if (!obj) return ''
  return Object.entries(obj)
    .filter(([_, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&')
}
