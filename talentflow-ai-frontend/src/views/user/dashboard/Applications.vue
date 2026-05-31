<template>
  <div class="app-page">
    <h3>我的投递记录</h3>
    <el-table :data="list" stripe v-loading="loading" style="width:100%">
      <el-table-column label="投递目标" min-width="200">
        <template #default="s">
          <div>{{ s.row.target_title }}</div>
          <div style="font-size:12px;color:#909399" v-if="s.row.company">{{ s.row.company }}</div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="100">
        <template #default="s">
          <el-tag :type="typeTag(s.row.target_type)" size="small">{{ s.row.target_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resume_title" label="使用简历" width="140" />
      <el-table-column label="状态" width="100">
        <template #default="s">
          <el-tag :type="statusTag(s.row.status)" size="small">{{ statusLabel(s.row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="投递时间" width="170">
        <template #default="s">{{ s.row.created_at?.slice(0, 16) }}</template>
      </el-table-column>
    </el-table>
    <div class="pagination-row" v-if="total > 10">
      <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="10" v-model:current-page="page" @current-change="(p) => fetchApps(p)" />
    </div>
    <el-empty v-if="!loading && !list.length" description="暂无投递记录" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '../../../utils/request'

const list = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)

const typeTag = t => ({ '智能投递': 'primary', '手动投递': 'info', '任务接单': 'success' }[t] || 'info')
const statusLabel = s => ({ applied: '已投递', approved: '已通过', rejected: '已驳回' }[s] || s)
const statusTag = s => ({ applied: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')

const fetchApps = async (p = 1) => {
  page.value = p
  loading.value = true
  try {
    const res = await request.get('/user/applications', { params: { skip: (p-1)*10, limit: 10 } })
    const d = res.data || res
    list.value = d.items || []; total.value = d.total || 0
  } finally { loading.value = false }
}

onMounted(() => fetchApps())
</script>

<style scoped>
.app-page { padding: 20px; }
.app-page h3 { margin: 0 0 20px 0; }
</style>
