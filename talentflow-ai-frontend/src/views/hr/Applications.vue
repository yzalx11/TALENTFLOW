<template>
  <div class="app-page">
    <!-- 子菜单 -->
    <div class="sub-header">
      <el-menu mode="horizontal" :default-active="activeTab" class="sub-menu" @select="(i) => activeTab = i">
        <el-menu-item index="task">任务投递</el-menu-item>
        <el-menu-item index="job">岗位投递</el-menu-item>
      </el-menu>
    </div>

    <!-- 任务投递表格 -->
    <el-table v-if="activeTab === 'task'" :data="taskApps" stripe v-loading="loading" style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="target_title" label="任务标题" min-width="160" />
      <el-table-column prop="category" label="分类" width="80" />
      <el-table-column label="赏金" width="100"><template #default="s">¥{{ s.row.price }}</template></el-table-column>
      <el-table-column prop="difficulty" label="难度" width="80" />
      <el-table-column prop="user_name" label="投递人" width="100" />
      <el-table-column label="投递时间" width="160"><template #default="s">{{ s.row.created_at?.slice(0, 16) }}</template></el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="s"><el-tag :type="statusTag(s.row.status)" size="small">{{ statusLabel(s.row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="s">
          <el-button v-if="s.row.status === 'applied'" size="small" type="primary" @click="openReview(s.row)">审核</el-button>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 岗位投递表格 -->
    <el-table v-if="activeTab === 'job'" :data="jobApps" stripe v-loading="loading" style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="target_title" label="岗位名称" min-width="160" />
      <el-table-column prop="company" label="公司" width="120" />
      <el-table-column prop="user_name" label="投递人" width="100" />
      <el-table-column label="求职信" min-width="160">
        <template #default="s">
          <span v-if="s.row.cover_letter">
            {{ s.row.cover_letter.slice(0, 40) }}{{ s.row.cover_letter.length > 40 ? '...' : '' }}
            <el-button link type="primary" size="small" @click="showLetter = s.row.cover_letter; letterVisible = true">详情</el-button>
          </span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="投递时间" width="160"><template #default="s">{{ s.row.created_at?.slice(0, 16) }}</template></el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="s"><el-tag :type="statusTag(s.row.status)" size="small">{{ statusLabel(s.row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="s">
          <el-button v-if="s.row.status === 'applied'" size="small" type="primary" @click="openReview(s.row)">审核</el-button>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !currentList.length" description="暂无投递记录" />

    <!-- 求职信弹窗 -->
    <el-dialog v-model="letterVisible" title="求职信全文" width="500px" @close="showLetter = ''; letterVisible = false">
      <p style="line-height:1.8;white-space:pre-wrap">{{ showLetter }}</p>
    </el-dialog>

    <!-- 审核弹窗 -->
    <el-dialog v-model="reviewVisible" title="审核投递" width="600px" destroy-on-close @close="resumeDetail = null">
      <div v-if="currentApp">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="投递人">{{ currentApp.user_name }}</el-descriptions-item>
          <el-descriptions-item label="投递目标">{{ currentApp.target_title }}</el-descriptions-item>
          <el-descriptions-item label="投递时间">{{ currentApp.created_at?.slice(0, 16) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(currentApp.status)" size="small">{{ statusLabel(currentApp.status) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">简历详情</el-divider>
        <div v-if="resumeDetail" v-loading="resumeLoading" class="resume-box">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="姓名">{{ resumeDetail.name }}</el-descriptions-item>
            <el-descriptions-item label="简历标题">{{ resumeDetail.title }}</el-descriptions-item>
            <el-descriptions-item label="学历">{{ resumeDetail.education || '-' }}</el-descriptions-item>
            <el-descriptions-item label="电话">{{ resumeDetail.phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邮箱" :span="2">{{ resumeDetail.email || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div class="section" v-if="resumeDetail.work_experience">
            <h4 class="section-title">工作经历</h4>
            <p class="resume-text">{{ resumeDetail.work_experience }}</p>
          </div>
          <div class="section" v-if="resumeDetail.project_experience">
            <h4 class="section-title">项目经验</h4>
            <p class="resume-text">{{ resumeDetail.project_experience }}</p>
          </div>
          <div class="section" v-if="resumeDetail.summary">
            <h4 class="section-title">自我评价</h4>
            <p class="resume-text">{{ resumeDetail.summary }}</p>
          </div>
          <div class="section" v-if="resumeDetail.skills?.length">
            <h4 class="section-title">技能</h4>
            <el-tag v-for="sk in resumeDetail.skills" :key="sk" size="small" effect="plain" style="margin:2px 4px 2px 0">{{ sk }}</el-tag>
          </div>
        </div>
        <div v-else-if="resumeLoading" style="text-align:center;padding:20px">加载简历中...</div>
        <el-empty v-else description="未关联简历" :image-size="40" />
      </div>

      <el-divider />
      <el-form label-width="80px">
        <el-form-item label="审核评语">
          <el-input v-model="reviewComment" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="doReview('reject')" type="danger" :loading="reviewLoading">驳回</el-button>
        <el-button @click="doReview('pass')" type="success" :loading="reviewLoading">通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from '../../utils/request'

const appList = ref([])
const loading = ref(false)
const activeTab = ref('task')

const taskApps = computed(() => appList.value.filter(a => a.target_type === '任务'))
const jobApps = computed(() => appList.value.filter(a => a.target_type === '岗位'))
const currentList = computed(() => activeTab.value === 'task' ? taskApps.value : jobApps.value)

const statusLabel = s => ({ applied: '待审核', approved: '已通过', rejected: '已驳回' }[s] || s)
const statusTag = s => ({ applied: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')

// 审核
const reviewVisible = ref(false); const reviewLoading = ref(false)
const reviewComment = ref(''); const currentApp = ref(null)

// 求职信
const showLetter = ref(''); const letterVisible = ref(false)

// 简历
const resumeDetail = ref(null); const resumeLoading = ref(false)

const fetchApps = async () => {
  loading.value = true
  try { const res = await axios.get('/mentor/applications'); appList.value = res.data || res }
  catch { ElMessage.error('加载投递列表失败') }
  finally { loading.value = false }
}

const openReview = async (row) => {
  currentApp.value = row; reviewComment.value = ''; resumeDetail.value = null
  reviewVisible.value = true
  // 有简历则自动加载
  if (row.resume_id) { resumeLoading.value = true; try { const r = await axios.get(`/mentor/resumes/${row.resume_id}`); resumeDetail.value = r.data || r } catch {} finally { resumeLoading.value = false } }
}

const doReview = async (action) => {
  reviewLoading.value = true
  try {
    await axios.post(`/mentor/applications/${currentApp.value.id}/review`, { action, review_comment: reviewComment.value })
    ElMessage.success(action === 'pass' ? '已通过' : '已驳回')
    reviewVisible.value = false; fetchApps()
  } catch (e) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
  finally { reviewLoading.value = false }
}

onMounted(fetchApps)
</script>

<style scoped>
.app-page { padding: 0; }
.sub-header { margin-bottom: 20px; }
.sub-menu { border-radius: 6px; }
.text-muted { color: #909399; }
.resume-name { font-weight: 600; font-size: 14px; color: #303133; margin: 0 0 4px 0; }
.resume-meta { font-size: 12px; color: #909399; margin: 0 0 6px 0; }
.resume-text { font-size: 12px; color: #606266; line-height: 1.6; margin: 4px 0; }
.resume-skills { margin-top: 6px; display: flex; flex-wrap: wrap; }
.section { margin-top: 12px; }
.section-title { font-size: 13px; font-weight: 600; color: #303133; margin: 0 0 6px 0; border-left: 3px solid #409EFF; padding-left: 8px; }
.resume-box { max-height: 400px; overflow-y: auto; }
</style>
