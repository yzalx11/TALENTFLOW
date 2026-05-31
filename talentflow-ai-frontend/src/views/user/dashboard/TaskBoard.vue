<template>
  <div class="taskboard-page">
    <div class="page-header">
      <h3>实战任务大厅</h3>
      <div class="header-right">
        <el-select v-model="sortBy" style="width:130px;margin-right:10px" @change="fetchTasks(1)">
          <el-option label="最新发布" value="created_at" />
          <el-option label="金额最高" value="price" />
        </el-select>
        <el-select v-model="currentDifficulty" style="width:100px;margin-right:10px" placeholder="难度" clearable @change="fetchTasks(1)">
          <el-option label="简单" value="简单" />
          <el-option label="中等" value="中等" />
          <el-option label="困难" value="困难" />
        </el-select>
        <el-radio-group v-model="currentCategory" size="small" @change="fetchTasks(1)">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="前端">前端</el-radio-button>
          <el-radio-button label="后端">后端</el-radio-button>
          <el-radio-button label="设计">设计</el-radio-button>
          <el-radio-button label="运维">运维</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="task-grid" v-loading="loading">
      <el-empty v-if="!loading && taskList.length === 0" description="暂无任务" />
      <div v-for="task in taskList" :key="task.id" class="task-card" @click="goToDetail(task.id)">
        <div class="card-header">
          <div>
            <el-tag :type="getTagColor(task.category)" size="small" effect="dark">{{ task.category }}</el-tag>
            <el-tag v-if="task.difficulty" size="small" type="info" effect="plain" style="margin-left:6px">{{ task.difficulty }}</el-tag>
          </div>
          <span class="price">¥{{ task.price }}</span>
        </div>
        <div class="card-body">
          <h4 class="title">{{ task.title }}</h4>
          <p class="desc">{{ task.description }}</p>
        </div>
        <div class="card-footer">
          <div class="meta">
            <div class="meta-row">
              <span>{{ task.duration || '?' }} 天</span>
              <span class="separator">|</span>
              <span>{{ task.mentor_name }}</span>
            </div>
            <div class="skills-row" v-if="task.skills?.length">
              <el-tag v-for="sk in task.skills.slice(0,3)" :key="sk" size="small" type="info" effect="light">{{ sk }}</el-tag>
            </div>
          </div>
          <el-button
            type="primary" size="small" plain
            :disabled="task.is_enrolled || task.status !== 1"
            @click.stop="handleApply(task)"
          >{{ task.is_enrolled ? '已报名' : task.status !== 1 ? '不可接单' : '立即接单' }}</el-button>
        </div>
      </div>
    </div>

    <div class="pagination" v-if="total > 10">
      <el-pagination
        v-model:current-page="page"
        :page-size="10"
        :total="total"
        layout="prev, pager, next"
        background
        @current-change="(p) => fetchTasks(p)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTaskList, applyTask } from '../../../api/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const taskList = ref([])
const currentCategory = ref('')
const currentDifficulty = ref('')
const sortBy = ref('created_at')
const page = ref(1)
const total = ref(0)

const fetchTasks = async (p = 1) => {
  page.value = p
  loading.value = true
  try {
    const res = await getTaskList({
      skip: (p - 1) * 10,
      limit: 10,
      category: currentCategory.value,
      difficulty: currentDifficulty.value,
      sort_by: sortBy.value,
    })
    const data = res.data || res
    taskList.value = data.items || []
    total.value = data.total || 0
  } catch {
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

const goToDetail = (id) => router.push({ name: 'TaskDetail', params: { id } })

const handleApply = async (task) => {
  try {
    await ElMessageBox.confirm(`确定接取任务 "${task.title}" 吗？`, '接单确认', { type: 'warning', confirmButtonText: '确定接单', cancelButtonText: '再想想' })
    await applyTask(task.id)
    ElMessage.success('接单成功，请等待导师审核')
    fetchTasks(page.value)
  } catch (e) {
    if (e !== 'cancel' && e?.response?.data?.detail) {
      ElMessage.warning(e.response.data.detail)
    }
  }
}

const getTagColor = (cat) => ({ '前端': 'primary', '后端': 'success', '设计': 'warning', '运维': 'danger' }[cat] || 'info')

onMounted(() => fetchTasks())
</script>

<style scoped>
.taskboard-page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: #fff; padding: 15px 20px; border-radius: 8px; }
.page-header h3 { margin: 0; font-size: 18px; color: #303133; }
.header-right { display: flex; align-items: center; }
.task-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; min-height: 200px; }
@media (max-width: 900px) { .task-grid { grid-template-columns: 1fr; } }
.task-card { background: #fff; border-radius: 8px; padding: 20px; border: 1px solid #e4e7ed; transition: all 0.3s; display: flex; flex-direction: column; cursor: pointer; }
.task-card:hover { transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-color: #409EFF; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.price { color: #F56C6C; font-size: 20px; font-weight: bold; }
.card-body { flex: 1; margin-bottom: 15px; }
.title { margin: 0 0 8px 0; font-size: 16px; color: #303133; }
.desc { margin: 0; font-size: 13px; color: #909399; line-height: 1.5; height: 40px; overflow: hidden; }
.card-footer { border-top: 1px solid #ebeef5; padding-top: 12px; display: flex; justify-content: space-between; align-items: center; }
.meta { display: flex; flex-direction: column; gap: 6px; }
.meta-row { font-size: 12px; color: #909399; }
.separator { margin: 0 8px; color: #dcdfe6; }
.skills-row { display: flex; gap: 4px; flex-wrap: wrap; }
.pagination { display: flex; justify-content: center; margin-top: 30px; }
</style>
