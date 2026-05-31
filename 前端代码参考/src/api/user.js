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
    url: `/user/recommend/${userId}`,
    method: 'get',
    params: {
      top_k: topK
    },
    // 重点：在这里增加 timeout 配置
    timeout: 240000, // 设置为 120秒，给后端足够的时间计算
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

// import { debounce } from 'lodash-es'; // 需要安装 lodash-es

// // 1. 提交任务 (防抖：防止用户连点)
// export const submitRecommendTask = debounce(async (userId) => {
//   const res = await request({
//     url: '/user/recommend/submit',
//     method: 'post',
//     data: { user_id: userId, top_k: 5 }
//   });
//   return res;
// }, 1000); // 1秒内重复调用只执行一次

// // 2. 轮询结果 (智能休眠)
// export const pollRecommendResult = async (taskId, maxTime = 30000) => {
//   let startTime = Date.now();
  
//   // 模拟指数退避的轮询
//   const attempt = async (delay = 1000) => {
//     // 超时控制
//     if (Date.now() - startTime > maxTime) {
//       throw new Error('请求超时');
//     }

//     try {
//       const res = await request({
//         url: `/user/recommend/status/${taskId}`,
//         method: 'get',
//         // 关键：告诉 Axios 不要缓存 GET 请求
//         headers: {
//           'Cache-Control': 'no-cache',
//           'Pragma': 'no-cache'
//         }
//       });

//       if (res.status === 'success') {
//         return res.data;
//       } else if (res.status === 'processing') {
//         // 未完成，递归调用，延迟时间翻倍 (1s, 2s, 4s...)
//         await new Promise(resolve => setTimeout(resolve, delay));
//         return attempt(delay * 2);
//       } else {
//         throw new Error(res.message || '任务异常');
//       }
//     } catch (error) {
//       throw error;
//     }
//   };

//   return attempt();
// };


// 1. 提交推荐任务
export const submitRecommendTask = (userId) => {
  // 显式返回一个 Promise，确保 Vue 组件中的 await 能正确捕获结果
  return new Promise((resolve, reject) => {
    request({
      url: '/user/recommend/submit',
      method: 'post',
      data: { user_id: userId, top_k: 5 }
    }).then(response => {
      // 核心修复：兼容拦截器是否自动解包 response.data
      // 如果 response 里有 data 且 data 里有 task_id，说明拦截器没解包，取 response.data
      // 否则说明拦截器已经解包了，直接用 response
      const res = response.data?.task_id ? response.data : response
      resolve(res)
    }).catch(error => {
      reject(error)
    })
  })
}

// 2. 轮询推荐结果
export const pollRecommendResult = (taskId, maxTime = 30000) => {
  return new Promise((resolve, reject) => {
    let startTime = Date.now();
    
    const attempt = async (delay = 1000) => {
      if (Date.now() - startTime > maxTime) {
        reject(new Error('请求超时'));
        return;
      }

      try {
        const response = await request({
          url: `/user/recommend/status/${taskId}`,
          method: 'get',
          headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });

        // 同样做一层数据解包兼容
        const res = response.data?.status ? response.data : response;

        if (res.status === 'success') {
          resolve(res.data); // 成功，把最终的职位数据 resolve 出去
        } else if (res.status === 'processing') {
          // 还在处理中，延迟后递归调用
          await new Promise(r => setTimeout(r, delay));
          return attempt(delay * 2); // 指数退避：1s, 2s, 4s...
        } else {
          reject(new Error(res.message || '任务异常'));
        }
      } catch (error) {
        reject(error);
      }
    };

    attempt();
  });
}
