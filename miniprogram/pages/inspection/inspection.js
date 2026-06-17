const api = require('../../../utils/api')

const ANGLES = [
  { key: 'front', label: '前保险杠', icon: '📷' },
  { key: 'rear', label: '后保险杠', icon: '📷' },
  { key: 'left', label: '左侧车身', icon: '📷' },
  { key: 'right', label: '右侧车身', icon: '📷' },
  { key: 'interior_front', label: '前排内饰', icon: '📷' },
  { key: 'interior_rear', label: '后排内饰', icon: '📷' },
  { key: 'dashboard', label: '仪表盘', icon: '📷' },
  { key: 'tires', label: '轮胎轮毂', icon: '📷' },
  { key: 'engine_bay', label: '发动机舱', icon: '📷' },
  { key: 'trunk', label: '后备箱', icon: '📷' },
]

Page({
  data: {
    orderId: null,
    angles: ANGLES,
    photos: {},        // { front: { tempPath: '...', size: 123 }, rear: { ... } }
    notes: '',
    mileage: '',
    fuelLevel: '',
    fuelOptions: ['满箱', '3/4', '半箱', '1/4', '少油'],
    fuelIndex: -1,
    submitting: false,
    isNew: true,
    _existingId: null,
  },

  onLoad(options) {
    const orderId = parseInt(options.orderId || options.order_id || '0')
    this.setData({ orderId })
    if (orderId) {
      this._loadExisting(orderId)
    }
  },

  async _loadExisting(orderId) {
    try {
      const res = await api.getInspection(orderId)
      if (res && res.id) {
        const photos = {}
        if (res.photos && res.photos.length) {
          res.photos.forEach(p => { photos[p.angle] = { tempPath: p.path, realPath: p.path } })
        }
        const fi = res.fuel_level ? this.data.fuelOptions.indexOf(res.fuel_level) : -1
        this.setData({
          photos,
          notes: res.notes || '',
          mileage: String(res.mileage || ''),
          fuelLevel: res.fuel_level || '',
          fuelIndex: fi,
          isNew: false,
          _existingId: res.id,
        })
      }
    } catch (e) {
      // 新建模式
    }
  },

  choosePhoto(e) {
    const key = e.currentTarget.dataset.key
    const self = this
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      quality: 70,
      success(res) {
        const file = res.tempFiles[0]
        const key2 = 'photos.' + key
        self.setData({
          [key2]: { tempPath: file.tempFilePath, size: file.size }
        })
      }
    })
  },

  removePhoto(e) {
    const key = e.currentTarget.dataset.key
    const key2 = 'photos.' + key
    this.setData({ [key2]: null })
  },

  previewPhoto(e) {
    const key = e.currentTarget.dataset.key
    const photo = this.data.photos[key]
    if (photo && photo.tempPath) {
      wx.previewImage({ urls: [photo.tempPath] })
    }
  },

  onNotesInput(e) {
    this.setData({ notes: e.detail.value })
  },

  onMileageInput(e) {
    this.setData({ mileage: e.detail.value })
  },

  onFuelChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({
      fuelIndex: idx,
      fuelLevel: this.data.fuelOptions[idx]
    })
  },

  async submit() {
    if (!this.data.orderId) {
      wx.showToast({ title: '缺少工单ID', icon: 'none' })
      return
    }

    this.setData({ submitting: true })

    // 收集照片数据
    const photoList = Object.entries(this.data.photos)
      .filter(([_, v]) => v && v.tempPath)
      .map(([angle, v]) => ({
        angle,
        path: v.tempPath
      }))

    const payload = {
      order_id: this.data.orderId,
      photos: photoList,
      notes: this.data.notes,
      mileage: this.data.mileage ? parseInt(this.data.mileage) : null,
      fuel_level: this.data.fuelLevel || null,
    }

    try {
      if (this.data.isNew) {
        await api.createInspection(payload)
      } else {
        await api.updateInspection(this.data._existingId, payload)
      }
      wx.showToast({ title: '保存成功', icon: 'success' })
      setTimeout(() => { wx.navigateBack() }, 1500)
    } catch (e) {
      wx.showToast({ title: '保存失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
