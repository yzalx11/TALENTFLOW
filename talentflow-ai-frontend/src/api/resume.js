import request from '../utils/request'

// 获取简历列表
export const getResumeListAPI = () => request({ url: '/user/resumes', method: 'GET' })

// 解析简历文件（不入库）
export const parseResumeFileAPI = (formData) => request({
  url: '/user/resumes/parse',
  method: 'POST',
  data: formData,
  headers: { 'Content-Type': 'multipart/form-data' }
})

// 创建简历
export const createResumeAPI = (data) => request({ url: '/user/resumes', method: 'POST', data })

// 删除简历
export const deleteResumeAPI = (id) => request({ url: `/user/resumes/${id}`, method: 'DELETE' })

// 设为默认
export const setDefaultResumeAPI = (id) => request({ url: `/user/resumes/${id}/default`, method: 'POST' })
