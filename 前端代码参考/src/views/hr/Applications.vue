<template>
  <div class="resume-management">
    <div class="header-actions mb-4">
      <h3>人才投递管理</h3>
    </div>

    <!-- 添加 loading 状态 -->
    <el-table :data="resumeList" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="name" label="候选人" width="140">
        <template #default="scope">
          <div class="user-info">
            <!-- 映射后端的 candidate_name -->
            <span class="name">{{ scope.row.candidate_name }}</span>
            <!-- 映射后端的 experience_years，如果存在则显示 -->
            <span v-if="scope.row.experience_years" class="exp">
              {{ scope.row.experience_years }}年经验
            </span>
          </div>
        </template>
      </el-table-column>

      <!-- 映射后端的 job_title -->
      <el-table-column prop="job_title" label="申请任务" width="180" />

      <!-- 映射后端的 job_skills -->
      <el-table-column prop="job_skills" label="核心技能" width="150" />

      <!-- 格式化后端返回的 applied_at 时间 -->
      <el-table-column prop="applied_at" label="投递时间" width="160">
        <template #default="scope">
          {{ formatDate(scope.row.applied_at) }}
        </template>
      </el-table-column>

      <el-table-column prop="status" label="当前状态" width="120">
        <template #default="scope">
          <el-tag :type="getStatusTag(scope.row.status)">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="操作" fixed="right" width="200">
        <template #default="scope">
          <el-button size="small" icon="View" @click="handleView(scope.row)">查看简历</el-button>
          <el-button size="small" type="primary" plain @click="handleAction(scope.row)">处理</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from '../../utils/request' // 假设你封装了 axios，路径请按实际情况调整

const resumeList = ref([])
const loading = ref(false)

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    // 调用我们在 FastAPI 中定义的接口
    const response = await axios.get('/hr/applications')
    resumeList.value = response
  } catch (error) {
    ElMessage.error('获取投递列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 页面加载时请求数据
onMounted(() => {
  fetchData()
})

// 辅助函数：格式化日期 (简单版，生产环境建议用 dayjs)
const formatDate = (dateString) => {
  if (!dateString) return ''
  return dateString.split('T')[0] // 将 2026-05-14T10:00:00 转为 2026-05-14
}

const getStatusTag = (status) => {
  if (status === '待沟通') return 'warning'
  if (status === '已录用') return 'success'
  if (status === '不合适') return 'info'
  return ''
}

const handleView = (row) => {
  ElMessage.info('查看简历 ID: ' + row.id)
  // 这里可以跳转路由或打开弹窗
}

const handleAction = (row) => {
  ElMessage.success('处理申请: ' + row.candidate_name)
  // 这里可以打开处理状态的弹窗
}
</script>

<style scoped>
.mb-4 {
  margin-bottom: 20px;
}
.user-info {
  display: flex;
  flex-direction: column;
}
.exp {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>