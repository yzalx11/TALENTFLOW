<template>
  <div class="dashboard-container">
    <!-- 1. 统计卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-blue"><el-icon><Bell /></el-icon></div>
            <div class="text-box">
              <p class="label">待审核</p>
              <p class="number">{{ stats.pending_reviews ?? '-' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-green"><el-icon><Clock /></el-icon></div>
            <div class="text-box">
              <p class="label">进行中</p>
              <p class="number">{{ stats.in_progress ?? '-' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-orange"><el-icon><Briefcase /></el-icon></div>
            <div class="text-box">
              <p class="label">累计发布</p>
              <p class="number">{{ stats.total_published ?? '-' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-purple"><el-icon><Wallet /></el-icon></div>
            <div class="text-box">
              <p class="label">累计赏金</p>
              <p class="number">¥{{ stats.total_bounty ?? 0 }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 2. 时间轴 + 快捷操作 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never" v-loading="timelineLoading">
          <template #header><span class="card-header">近期任务动态</span></template>
          <el-timeline v-if="timeline.length">
            <el-timeline-item
              v-for="item in timeline"
              :key="item.event_time + item.event_type"
              :timestamp="item.event_time?.slice(0, 16)"
              :color="item.event_type === 'new_delivery' ? '#E6A23C' : '#409EFF'"
              placement="top"
            >
              <el-card shadow="hover" class="timeline-card"
                @click="item.ref_status === 'applied' ? openReviewFor(item) : null"
                :style="item.ref_status === 'applied' ? 'cursor: pointer' : ''"
              >
                <h4>{{ item.title }}</h4>
                <p>{{ item.user_name }} — {{ item.detail }}</p>
                <el-tag v-if="item.ref_status === 'applied'" type="warning" size="small">待审核</el-tag>
                <el-tag v-else-if="item.ref_status === 'approved'" type="success" size="small">已通过</el-tag>
                <el-tag v-else-if="item.ref_status === 'rejected'" type="danger" size="small">已驳回</el-tag>
              </el-card>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无动态" />
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never">
          <template #header><span class="card-header">快捷操作</span></template>
          <div class="quick-actions">
            <el-button type="primary" class="w-100 mb-2" @click="openPublishDialog">
              <el-icon><Plus /></el-icon>发布新任务
            </el-button>
            <el-button class="w-100 mb-2" @click="fetchAll">
              <el-icon><Refresh /></el-icon>刷新数据
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 3. 发布任务弹窗 -->
    <el-dialog v-model="publishVisible" title="发布新任务" width="550px" destroy-on-close>
      <el-form :model="taskForm" :rules="taskRules" ref="taskFormRef" label-width="80px">
        <el-form-item label="任务标题" prop="title">
          <el-input v-model="taskForm.title" placeholder="如：前端开发任务" />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="taskForm.description" type="textarea" :rows="3" placeholder="描述任务内容和要求" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类" prop="category">
              <el-select v-model="taskForm.category" style="width:100%">
                <el-option label="前端" value="前端" />
                <el-option label="后端" value="后端" />
                <el-option label="设计" value="设计" />
                <el-option label="DevOps" value="DevOps" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="难度">
              <el-select v-model="taskForm.difficulty" style="width:100%">
                <el-option label="简单" value="简单" />
                <el-option label="中等" value="中等" />
                <el-option label="困难" value="困难" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="赏金" prop="price">
              <el-input-number v-model="taskForm.price" :min="1" :step="50" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工期(天)">
              <el-input-number v-model="taskForm.duration" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="技能要求">
          <el-select v-model="taskForm.skills" multiple filterable allow-create default-first-option placeholder="输入技能后回车" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="publishVisible = false">取消</el-button>
        <el-button type="primary" :loading="publishLoading" @click="submitPublish">发布</el-button>
      </template>
    </el-dialog>

    <!-- 4. 审核弹窗 -->
    <el-dialog v-model="reviewVisible" title="审核投递" width="500px" destroy-on-close>
      <div v-if="currentApp">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="任务">{{ currentApp.title }}</el-descriptions-item>
          <el-descriptions-item label="投递人">{{ currentApp.user_name }}</el-descriptions-item>
          <el-descriptions-item label="投递时间">{{ currentApp.event_time?.slice(0, 16) }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <el-form label-width="80px">
          <el-form-item label="审核评语">
            <el-input v-model="reviewComment" type="textarea" :rows="2" placeholder="选填" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="doReview('reject')" type="danger" :loading="reviewLoading">驳回</el-button>
        <el-button @click="doReview('pass')" type="success" :loading="reviewLoading">通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Briefcase, Clock, Bell, Wallet, Plus, Refresh } from '@element-plus/icons-vue'
import axios from '../../utils/request'

// --- 统计 ---
const stats = reactive({ pending_reviews: 0, in_progress: 0, total_published: 0, total_bounty: 0 })

// --- 时间轴 ---
const timeline = ref([])
const timelineLoading = ref(false)

// --- 发布 ---
const publishVisible = ref(false)
const publishLoading = ref(false)
const taskFormRef = ref(null)
const taskForm = reactive({ title: '', description: '', category: '前端', difficulty: '中等', price: 100, duration: 7, skills: [], status: 1 })
const taskRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  price: [{ required: true, message: '请设置赏金', trigger: 'blur' }],
}

// --- 审核 ---
const reviewVisible = ref(false)
const reviewLoading = ref(false)
const reviewComment = ref('')
const currentApp = ref(null)

// --- 获取数据 ---
const fetchStats = async () => {
  try {
    const res = await axios.get('/mentor/stats')
    Object.assign(stats, res.data || res)
  } catch { /* 非导师角色 403，静默 */ }
}

const fetchTimeline = async () => {
  timelineLoading.value = true
  try {
    const res = await axios.get('/mentor/timeline', { params: { limit: 15 } })
    timeline.value = res.data || res
  } catch { timeline.value = [] }
  finally { timelineLoading.value = false }
}

const fetchAll = () => { fetchStats(); fetchTimeline() }

// --- 发布 ---
const openPublishDialog = () => {
  Object.assign(taskForm, { title: '', description: '', category: '前端', difficulty: '中等', price: 100, duration: 7, skills: [], status: 1 })
  publishVisible.value = true
}

const submitPublish = async () => {
  if (!taskFormRef.value) return
  await taskFormRef.value.validate(async (valid) => {
    if (!valid) return
    publishLoading.value = true
    try {
      await axios.post('/mentor/tasks', {
        title: taskForm.title,
        description: taskForm.description,
        category: taskForm.category,
        difficulty: taskForm.difficulty,
        price: taskForm.price,
        duration: taskForm.duration,
        skills: taskForm.skills || [],
      })
      ElMessage.success('任务发布成功')
      publishVisible.value = false
      fetchAll()
    } catch { ElMessage.error('发布失败') }
    finally { publishLoading.value = false }
  })
}

// --- 审核 ---
const openReviewFor = (item) => {
  // 从时间轴事件中提取 application_id（需后端在 timeline 中返回）
  reviewComment.value = ''
  currentApp.value = item
  reviewVisible.value = true
}

const doReview = async (action) => {
  reviewLoading.value = true
  try {
    const appId = currentApp.value?.ref_id
    if (!appId) {
      ElMessage.warning('无法定位投递记录')
      reviewLoading.value = false
      return
    }
    await axios.post(`/mentor/applications/${appId}/review`, {
      action,
      review_comment: reviewComment.value,
    })
    ElMessage.success(action === 'pass' ? '审核通过' : '已驳回')
    reviewVisible.value = false
    fetchAll()
  } catch { ElMessage.error('审核失败') }
  finally { reviewLoading.value = false }
}

onMounted(fetchAll)
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }
.mb-2 { margin-bottom: 10px; }
.w-100 { width: 100%; }

.stat-card { border-radius: 8px; }
.card-content { display: flex; align-items: center; }
.icon-box {
  width: 50px; height: 50px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 24px; margin-right: 15px;
}
.bg-blue { background-color: #409EFF; }
.bg-green { background-color: #67C23A; }
.bg-orange { background-color: #E6A23C; }
.bg-purple { background-color: #909399; }
.number { font-size: 24px; font-weight: bold; color: #303133; margin: 0; }
.label { font-size: 14px; color: #606266; margin: 0; }
.card-header { font-weight: 600; font-size: 15px; }
.timeline-card h4 { margin: 0 0 6px 0; font-size: 14px; }
.timeline-card p { margin: 0; font-size: 13px; color: #909399; }
.quick-actions { display: flex; flex-direction: column; }
</style>
