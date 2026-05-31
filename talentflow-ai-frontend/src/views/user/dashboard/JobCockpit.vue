<template>
  <div class="cockpit-container">
    <!-- 1. 顶部数据看板 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="item in statsData" :key="item.label">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-wrapper" :style="{ backgroundColor: item.color }">
              <el-icon :size="24" color="#fff">
                <component :is="item.icon" />
              </el-icon>
            </div>
            <div class="text-wrapper">
              <p class="label">{{ item.label }}</p>
              <p class="value">{{ item.value }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="main-content">
      <!-- 2. 左侧核心功能区 -->
      <el-col :span="16">
        <el-card shadow="never" class="function-card">
          <template #header>
            <div class="card-header">
              <span>核心功能</span>
            </div>
          </template>
          <div class="function-grid">
            <div class="func-item" @click="goToTaskHall">
              <el-icon :size="40" color="#409EFF"><Search /></el-icon>
              <span>寻找新机会</span>
            </div>
            <div class="func-item" @click="goToMyApplications">
              <el-icon :size="40" color="#67C23A"><Document /></el-icon>
              <span>我的投递记录</span>
            </div>
            <div class="func-item" @click="goToResume">
              <el-icon :size="40" color="#E6A23C"><List /></el-icon>
              <span>管理我的简历</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 3. 右侧智能推荐区 -->
      <el-col :span="8">
        <el-card shadow="never" class="recommend-card" v-loading="pageLoading">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <span>平台推荐</span>
                <el-tooltip content="基于您的简历和RAG技术智能匹配">
                  <el-icon class="question-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
              <div style="display:flex;align-items:center;gap:10px">
                <el-button size="small" type="success" @click="runAgentAutoApply" :loading="agentLoading">
                  🚀 一键智能投递
                </el-button>
                <el-tooltip content="刷新推荐列表">
                  <el-icon class="refresh-icon" :class="{ 'is-rotating': pageLoading }" @click="fetchRecommendations"><Refresh /></el-icon>
                </el-tooltip>
              </div>
            </div>
          </template>

          <div class="scroll-container">
            <el-pull-refresh v-model="isRefreshing" @refresh="onRefresh" :pull-distance="60">
              <!-- 空状态 -->
              <div v-if="recommendedJobs.length === 0" class="empty-jobs">
                <el-empty :image-size="100" description="暂无推荐职位">
                  <el-button type="primary" @click="fetchRecommendations">点击刷新</el-button>
                </el-empty>
              </div>

              <!-- 职位列表 -->
              <div v-else class="job-list">
                <div v-for="(item, index) in recommendedJobs" :key="item.job.id" class="job-item">
                  <div class="score-tag" :class="scoreClass(item.score)">匹配度 {{ item.score }}%</div>
                  <h3 class="job-title">{{ item.job.title }}</h3>
                  <div class="job-meta">
                    <span>{{ item.job.company }}</span>
                    <span class="salary">{{ item.job.salary }}</span>
                  </div>
                  <div class="skills">
                    <el-tag 
                      v-for="skill in item.matched_skills" 
                      :key="skill" 
                      size="small" 
                      class="skill-tag"
                    >
                      {{ skill }}
                    </el-tag>
                  </div>
                  <div class="action-area">
                    <el-button link type="primary" size="small" @click="openRadar(item)">能力对比</el-button>
                    <el-button link type="primary" size="small" @click="openApplyDialog(item)">投递简历</el-button>
                    <el-button link type="info" size="small" @click="showJobDetail(item.job)">查看详情</el-button>
                  </div>
                  <el-divider />
                </div>
              </div>
            </el-pull-refresh>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <!-- 投递简历弹窗 -->
    <el-dialog v-model="applyVisible" title="选择简历投递" width="420px" destroy-on-close>
      <p style="margin:0 0 12px;color:#606266">将投递至: <b>{{ applyTarget?.job?.title || applyTarget?.title }}</b></p>
      <el-radio-group v-model="selectedResumeId" v-if="resumeList.length">
        <div v-for="r in resumeList" :key="r.id" style="margin-bottom:10px">
          <el-radio :value="r.id">
            {{ r.title || r.name }}
            <el-tag v-if="r.is_default" size="small" type="success" effect="plain" style="margin-left:6px">默认</el-tag>
          </el-radio>
        </div>
      </el-radio-group>
      <el-empty v-else description="暂无简历，请先创建" :image-size="60" />
      <template #footer>
        <el-button @click="applyVisible = false">取消</el-button>
        <el-button type="primary" :loading="applyLoading" :disabled="!selectedResumeId" @click="confirmApply">确认投递</el-button>
      </template>
    </el-dialog>

    <!-- 岗位详情弹窗 -->
    <el-dialog v-model="jobDetailVisible" :title="previewJob?.title" width="500px" destroy-on-close>
      <el-descriptions v-if="previewJob" :column="1" border size="small">
        <el-descriptions-item label="公司">{{ previewJob.company }}</el-descriptions-item>
        <el-descriptions-item label="薪资">{{ previewJob.salary || '面议' }}</el-descriptions-item>
        <el-descriptions-item label="地点">{{ previewJob.location || '不限' }}</el-descriptions-item>
        <el-descriptions-item label="要求技能">{{ (previewJob.required_skills || []).join(', ') }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ previewJob.description }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 雷达图弹窗 -->
    <el-dialog v-model="radarVisible" title="能力对比分析" width="550px" destroy-on-close>
      <div ref="radarChart" style="width:100%;height:400px"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Search, 
  List, 
  Document, 
  QuestionFilled, 
  Refresh 
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 1. 引入 Pinia Store
// 注意：请确保路径正确，通常位于 src/store/
import { useUserStore } from '../../../store/user'
import { useResumeStore } from '../../../store/resume' // 需要创建这个文件

// 2. 引入 API (请确保路径正确)
import { submitRecommend, pollRecommend } from '../../../api/user'
import { getResumeListAPI } from '../../../api/resume'
import request from '../../../utils/request'
import * as echarts from 'echarts'

const router = useRouter()
const userStore = useUserStore()
const resumeStore = useResumeStore()

// --- 数据定义 ---
const pageLoading = ref(false)
const isRefreshing = ref(false)
const recommendedJobs = ref([])

// 顶部统计数据
const statsData = ref([
  { label: '累计收益', value: '¥ 0.00', icon: 'Wallet', color: '#67C23A' },
  { label: '简历浏览量', value: 128, icon: 'TrendCharts', color: '#409EFF' },
  { label: '面试邀请', value: 5, icon: 'Document', color: '#E6A23C' },
  { label: '待处理事项', value: 2, icon: 'List', color: '#F56C6C' },
])

// --- 核心逻辑：获取用户 ID (基于你提供的 Store 结构) ---
// 因为 userInfo 是对象，所以取 id 字段
const currentUserId = computed(() => userStore.userInfo?.id)

// --- 页面跳转 ---
const goToTaskHall = () => router.push('/dashboard/tasks')
const goToMyApplications = () => router.push('/dashboard/applications')
const goToResume = () => router.push('/dashboard/resume')

// --- 核心逻辑：异步推荐（submit + poll） ---
const pollingTimer = ref(null)

const fetchRecommendations = async () => {
  pageLoading.value = true
  recommendedJobs.value = []
  try {
    // Step 1: 提交异步任务
    const taskRes = await submitRecommend()
    const taskId = taskRes.task_id || taskRes.taskId
    if (!taskId) { ElMessage.error('提交推荐失败'); pageLoading.value = false; return }

    // Step 2: 轮询结果
    let attempts = 0
    const poll = async () => {
      const result = await pollRecommend(taskId)
      attempts++
      if (result.status === 'SUCCESS') {
        const recs = result.data?.recommendations || []
        recommendedJobs.value = recs.map(r => ({
          job: {
            id: r.job_id, title: r.title, company: r.company,
            salary: r.salary, location: r.location,
            description: r.description, required_skills: r.required_skills,
          },
          score: r.score,
          matched_skills: r.matched_skills,
          required_skills: r.required_skills,
          loading: false,
        }))
        pageLoading.value = false
        isRefreshing.value = false
        ElMessage.success(`AI 推荐完成，共 ${recs.length} 个职位`)
      } else if (result.status === 'FAILURE') {
        ElMessage.error('推荐计算失败')
        pageLoading.value = false
      } else if (attempts < 30) {
        pollingTimer.value = setTimeout(poll, 1500)
      } else {
        ElMessage.warning('推荐计算超时，请稍后刷新')
        pageLoading.value = false
      }
    }
    poll()
  } catch (error) {
    console.error('推荐请求失败:', error)
    ElMessage.error('推荐服务暂不可用')
    pageLoading.value = false
  }
}

// 三色打分 (PPT: ≥90绿, 70-89橙, <70红)
const scoreClass = (s) => s >= 90 ? 'score-high' : s >= 70 ? 'score-mid' : 'score-low'

// 雷达图
const radarVisible = ref(false)
const radarChart = ref(null)
let radarInstance = null

const jobDetailVisible = ref(false)
const previewJob = ref(null)
const showJobDetail = (job) => { previewJob.value = job; jobDetailVisible.value = true }

const dimMap = {
  '后端开发': ['python','java','go','fastapi','django','flask','spring','springboot','gin'],
  '前端基础': ['react','vue','typescript','javascript','next.js','tailwindcss','vite','html','css','node.js'],
  '数据库':   ['mysql','redis','postgresql','mongodb','elasticsearch','sql','milvus','chroma'],
  '中间件':   ['docker','k8s','kubernetes','nginx','kafka','grpc','git','linux','ci/cd'],
  '算法/AI':  ['pytorch','tensorflow','langchain','rag','llm','nlp','深度学习','机器学习','prompt','agent','lora'],
}

const scoreDim = (skills, dim) => {
  const kw = dimMap[dim] || []
  const hits = (skills || []).filter(s => kw.some(k => s.toLowerCase().includes(k))).length
  return Math.min(100, hits * 25 + 25)
}

const buildRadar = (job) => {
  const dims = Object.keys(dimMap)
  const userScores = dims.map(d => scoreDim(job.matched_skills, d))
  const jobScores = dims.map(d => scoreDim(job.required_skills || [], d))
  return {
    tooltip: {},
    legend: { data: ['你的能力', '职位要求'], bottom: 0 },
    radar: {
      radius: '60%',
      indicator: dims.map(d => ({ name: d, max: 100 })),
    },
    series: [{
      type: 'radar',
      data: [
        { value: userScores, name: '你的能力', areaStyle: { color: 'rgba(64,158,255,0.25)' }, lineStyle: { color: '#409EFF' }, itemStyle: { color: '#409EFF' } },
        { value: jobScores, name: '职位要求', areaStyle: { color: 'rgba(230,162,60,0.25)' }, lineStyle: { color: '#E6A23C' }, itemStyle: { color: '#E6A23C' } },
      ],
    }],
  }
}

const openRadar = (job) => {
  radarVisible.value = true
  setTimeout(() => {
    if (radarChart.value) {
      radarInstance?.dispose()
      radarInstance = echarts.init(radarChart.value)
      radarInstance.setOption(buildRadar(job))
    }
  }, 150)
}

const onRefresh = () => {
  fetchRecommendations()
}

// --- 单个投递（带简历选择）---
const applyVisible = ref(false)
const applyLoading = ref(false)
const applyTarget = ref(null)
const resumeList = ref([])
const selectedResumeId = ref(null)

const openApplyDialog = async (item) => {
  applyTarget.value = item
  selectedResumeId.value = null
  applyVisible.value = true
  try {
    const res = await getResumeListAPI()
    const data = res.data || res
    resumeList.value = data || []
    const dft = resumeList.value.find(r => r.is_default)
    if (dft) selectedResumeId.value = dft.id
    else if (resumeList.value.length === 1) selectedResumeId.value = resumeList.value[0].id
  } catch { ElMessage.error('获取简历列表失败') }
}

const confirmApply = async () => {
  applyLoading.value = true
  try {
    const jobId = applyTarget.value?.job?.id || applyTarget.value?.job_id
    await request.post('/user/smart-deliver', { job_id: jobId, mode: 'auto' })
    ElMessage.success('投递成功')
    applyVisible.value = false
  } catch (e) {
    const detail = e?.response?.data?.detail
    ElMessage.warning(typeof detail === 'string' ? detail : '投递失败')
  } finally { applyLoading.value = false }
}

// --- Agent 一键智能投递 ---
const agentLoading = ref(false)

const runAgentAutoApply = async () => {
  agentLoading.value = true
  try {
    const res = await request.post('/user/agent/apply', { mode: 'auto', threshold: 60 })
    const data = res.data || res
    if (data.success) {
      ElMessage.success(data.message || `已投递 ${data.applied?.length || 0} 个岗位`)
    } else {
      ElMessage.warning(data.message || '无匹配岗位')
    }
  } catch { ElMessage.error('智能投递失败') }
  finally { agentLoading.value = false }
}


// --- 初始化 ---
onMounted(() => {
  fetchRecommendations()
})

onBeforeUnmount(() => {
  clearTimeout(pollingTimer.value)
  radarInstance?.dispose()
})
</script>

<style scoped>
.cockpit-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

/* 统计卡片样式 */
.stats-row {
  margin-bottom: 20px;
}
.stat-card {
  border-radius: 8px;
}
.card-content {
  display: flex;
  align-items: center;
}
.icon-wrapper {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}
.text-wrapper .label {
  font-size: 14px;
  color: #999;
  margin: 0;
}
.text-wrapper .value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  margin: 5px 0 0;
}

/* 主体布局 */
.main-content {
  display: flex;
}

/* 左侧功能区 */
.function-card {
  border-radius: 8px;
}
.function-grid {
  display: flex;
  justify-content: space-around;
  padding: 20px 0;
  text-align: center;
}
.func-item {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.2s;
}
.func-item:hover {
  transform: translateY(-5px);
  color: #409EFF;
}
.func-item span {
  margin-top: 10px;
  font-size: 16px;
  font-weight: 500;
}

/* 右侧推荐区 */
.recommend-card {
  border-radius: 8px;
  height: 800px;
  display: flex;
  flex-direction: column;
}

/* 头部样式修改 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.question-icon {
  color: #909399;
  cursor: help;
}

/* 刷新按钮样式 */
.refresh-icon {
  font-size: 18px;
  color: #909399;
  cursor: pointer;
  transition: transform 0.3s;
}
.refresh-icon:hover {
  color: #409EFF;
}
/* 旋转动画 */
.is-rotating {
  animation: rotate 1s linear infinite;
}
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 滚动容器 */
.scroll-container {
  flex: 1;
  overflow-y: auto;
  height: 100%;
}
.job-item {
  margin-bottom: 10px;
  position: relative;
}
.score-tag {
  position: absolute;
  top: 0;
  right: 0;
  color: white;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
}
.score-high { background-color: #67C23A; }
.score-mid  { background-color: #E6A23C; }
.score-low  { background-color: #F56C6C; }
.job-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin: 0 0 8px 0;
  line-height: 1.4;
  padding-right: 60px;
}
.job-meta {
  font-size: 13px;
  color: #999;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
}
.salary {
  color: #F56C6C;
  font-weight: bold;
}
.skills {
  margin-bottom: 15px;
}
.skill-tag {
  margin-right: 5px;
  margin-bottom: 5px;
  background-color: #f0f2f5;
  color: #606266;
  border: none;
}
.action-area {
  text-align: right;
}

/* 滚动条样式 */
.scroll-container::-webkit-scrollbar {
  width: 6px;
}
.scroll-container::-webkit-scrollbar-thumb {
  background-color: #ddd;
  border-radius: 3px;
}
</style>