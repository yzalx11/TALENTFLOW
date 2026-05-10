<template>
  <div class="resume-management">
    <div class="header-actions mb-4">
      <h3>人才投递管理</h3>
    </div>

    <el-table :data="resumeList" stripe style="width: 100%">
      <el-table-column prop="name" label="候选人" width="120">
        <template #default="scope">
          <div class="user-info">
            <span class="name">{{ scope.row.name }}</span>
            <span class="exp">{{ scope.row.experience }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="task" label="申请任务" width="180" />
      <el-table-column prop="skill" label="核心技能" width="150" />
      <el-table-column prop="date" label="投递时间" width="160" />

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
import { ElMessage } from 'element-plus'

const resumeList = [
  { id: 1, name: '李四', experience: '3年经验', task: '企业官网前端开发', skill: 'Vue3, TS', date: '2026-05-02', status: '待沟通' },
  { id: 2, name: '王五', experience: '5年经验', task: 'Python 爬虫脚本编写', skill: 'Python, Scrapy', date: '2026-05-01', status: '已录用' },
]

const getStatusTag = (status) => {
  if (status === '待沟通') return 'warning'
  if (status === '已录用') return 'success'
  return 'info'
}

const handleView = (row) => { ElMessage.info('查看简历详情: ' + row.name) }
const handleAction = (row) => { ElMessage.info('处理申请: ' + row.name) }
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }
.user-info { display: flex; flex-direction: column; }
.exp { font-size: 12px; color: #999; }
</style>