<template>
  <div class="task-management">
    <!-- 顶部操作栏 -->
    <div class="header-actions mb-4">
      <el-button type="primary" icon="Plus" @click="handleCreate">发布新任务</el-button>
      <el-input v-model="searchQuery" placeholder="搜索任务标题..." style="width: 240px; margin-left: 10px;" />
    </div>

    <!-- 任务列表表格 -->
    <el-table :data="taskList" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="任务标题" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column prop="budget" label="预算" width="100">
        <template #default="scope">¥{{ scope.row.budget }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.status === '进行中' ? 'success' : scope.row.status === '待审核' ? 'warning' : 'info'">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="applications" label="投递数" width="80" />
      <el-table-column prop="date" label="发布时间" width="160" />

      <el-table-column label="操作" fixed="right" width="200">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination mt-4">
      <el-pagination background layout="prev, pager, next" :total="100" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'

const searchQuery = ref('')

// 模拟数据
const taskList = ref([
  { id: 101, title: '企业官网前端开发', category: '前端', budget: 5000, status: '进行中', applications: 12, date: '2026-04-28' },
  { id: 102, title: 'Logo 设计 VI 规范', category: '设计', budget: 1200, status: '待审核', applications: 0, date: '2026-05-01' },
  { id: 103, title: 'Python 爬虫脚本编写', category: '后端', budget: 800, status: '已结束', applications: 5, date: '2026-04-20' },
])

const handleCreate = () => { ElMessage.info('跳转发布页面') }
const handleEdit = (row) => { ElMessage.info('编辑任务 ID: ' + row.id) }
const handleDelete = (id) => {
  ElMessageBox.confirm('确定要删除该任务吗？', '警告', { type: 'warning' }).then(() => {
    ElMessage.success('删除成功')
  })
}
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }
.mt-4 { margin-top: 20px; }
</style>