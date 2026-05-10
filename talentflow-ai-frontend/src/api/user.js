import request from '../utils/request'

// 1. 获取实战任务列表
// 对应后端：GET /api/v1/user/tasks/
export function getTaskList(params) {
  return request({
    url: '/user/tasks/',
    method: 'get',
    params // 支持传递 category, status 等查询参数
  })
}

// 2. 获取任务详情
// 对应后端：GET /api/v1/user/tasks/{task_id}
export function getTaskDetail(taskId) {
  return request({
    url: `/user/tasks/${taskId}`,
    method: 'get'
  })
}

// 3. 立即接单 (提交任务申请)
// 对应后端：POST /api/v1/user/tasks/{task_id}/apply (假设的接单接口)
export function applyTask(taskId) {
  return request({
    url: `/user/tasks/${taskId}/apply`,
    method: 'post',
    // 不需要传 data，后端从 Token 里拿用户信息
  })
}


// 4. 获取推荐职位列表 (RAG 推荐)
export function getRecommendedJobs(userId, topK = 5) {
  return request({
    url: `/user/recommend1/${userId}`,
    method: 'get',
    params: {
      top_k: topK
    },
    // 重点：在这里增加 timeout 配置
    timeout: 60000, // 设置为 60秒，给后端足够的时间计算
    // 如果你的 request 实例不支持单独配置 timeout，请看第二步
  })
}

export function smartApply(data) {
  return request({
    url: '/user/smart-apply',
    method: 'post',
    data: data
  })
}
