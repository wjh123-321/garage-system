Page({
  data: {
    imageSrc: null,
    result: null,
    loading: false
  },
  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image']
    }).then(r => {
      this.setData({ imageSrc: r.tempFiles[0].tempFilePath });
      this.analyze(r.tempFiles[0].tempFilePath);
    });
  },
  async analyze(path) {
    this.setData({ loading: true });
    wx.getFileSystemManager().readFile({
      filePath: path,
      encoding: 'base64',
      success: (data) => {
        wx.request({
          url: getApp().globalData.baseUrl + '/vision/analyze',
          method: 'POST',
          data: { image_base64: data.data },
          success: r => this.setData({ result: r.data, loading: false }),
          fail: () => this.setData({ loading: false })
        });
      }
    });
  }
});
