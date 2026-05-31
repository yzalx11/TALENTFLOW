// api/job.js
import request from '../utils/request' // 假设你有这个封装


// 解析文档接口
export const uploadParseFileApi = (data) => {
  return request({
    url: '/jobs/parse',
    method: 'post',
    data: data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}