import request from '../utils/request'

// 1. 获取任务列表（任务广场）
export function getTaskList(params = {}) {
  return request({
    url: '/user/tasks',
    method: 'get',
    params: {
      skip: params.skip || 0,
      limit: params.limit || 10,
      keyword: params.keyword || '',
      category: params.category || '',
      difficulty: params.difficulty || '',
      sort_by: params.sort_by || 'created_at',
    }
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

// 3. 立即接单
export function applyTask(taskId) {
  return request({
    url: `/user/tasks/${taskId}/apply`,
    method: 'post',
  })
}


// 4. AI 推荐（异步）— 提交任务
export function submitRecommend() {
  return request({
    url: '/user/recommend',
    method: 'post',
  })
}

// 5. AI 推荐（异步）— 轮询结果
export function pollRecommend(taskId) {
  return request({
    url: `/user/recommend/${taskId}`,
    method: 'get',
  })
}

// 6. 单岗位智能投递
export function smartApply(jobId) {
  return request({
    url: `/user/jobs/${jobId}/apply`,
    method: 'post',
  })
}
