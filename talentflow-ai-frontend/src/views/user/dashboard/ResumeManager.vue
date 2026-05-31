<template>
  <div class="resume-manager">
    <!-- 顶部操作栏 -->
    <div class="header">
      <h2>我的简历库</h2>
      <el-button type="primary" icon="Plus" @click="handleCreate">新建简历</el-button>
    </div>

    <!-- 简历列表 -->
    <el-row :gutter="20">
      <el-col :span="8" v-for="resume in resumeList" :key="resume.id">
        <el-card 
          class="resume-card" 
          :body-style="{ padding: '20px' }"
          :class="{ 'is-active': resume.id === currentResumeId }"
          shadow="hover"
        >
          <div class="card-header">
            <span class="title">{{ resume.title || '未命名简历' }}</span>
            <div>
              <el-tag :type="statusType(resume.status)" size="small" style="margin-right:4px">{{ statusText(resume.status) }}</el-tag>
              <el-tag v-if="resume.is_default" type="success" size="small">默认</el-tag>
            </div>
          </div>
          
          <div class="card-body">
            <p><i class="el-icon-user"></i> {{ resume.name || '未填写姓名' }}</p>
            <p><i class="el-icon-phone"></i> {{ resume.phone || '未填写电话' }}</p>
            <p><i class="el-icon-date"></i> 更新: {{ formatDate(resume.updated_at) }}</p>
          </div>

          <div class="card-footer">
            <el-button link type="primary" size="small" @click="handleEdit(resume)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(resume.id)">删除</el-button>
            <div class="footer-right" v-if="resume.status === 'reviewed'">
              <el-button v-if="resume.id !== currentResumeId" size="small" type="primary" plain @click="selectResume(resume)">使用此简历</el-button>
              <el-tag v-else type="success" size="small" effect="dark">使用中</el-tag>
            </div>
            <el-tag v-else type="info" size="small">等待审核</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ================= 完整编辑弹窗 ================= -->
   <!-- 新建/编辑简历的完整弹窗 -->
    <el-dialog 
    :title="isEdit ? '编辑简历' : '新建简历'" 
    v-model="dialogVisible"
    width="600px"
    >
    <el-form :model="form" label-position="top">

        <!-- 上传简历文件（仅新建） -->
        <div v-if="!isEdit" style="margin-bottom:16px">
          <el-upload
            class="upload-demo"
            drag
            :auto-upload="true"
            :show-file-list="true"
            :limit="1"
            accept=".pdf,.doc,.docx,.txt"
            :http-request="handleUploadParse"
            :on-remove="() => uploadFile = null"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">拖拽简历文件 或 <em>点击上传</em></div>
            <template #tip><div class="el-upload__tip">支持 PDF/DOCX/TXT，上传后自动解析并填充下方表单</div></template>
          </el-upload>
          <el-divider />
        </div>

        <!-- 1. 基础信息 -->
        <el-divider content-position="left">基础信息</el-divider>
        <el-row :gutter="20">
        <el-col :span="12">
            <el-form-item label="简历标题">
            <el-input v-model="form.title" placeholder="例如：张三的React前端简历"></el-input>
            </el-form-item>
        </el-col>
        <el-col :span="12">
            <el-form-item label="姓名">
            <el-input v-model="form.name" placeholder="您的姓名"></el-input>
            </el-form-item>
        </el-col>
        </el-row>
        
        <el-row :gutter="20">
        <el-col :span="12">
            <el-form-item label="学历">
            <el-select v-model="form.education" placeholder="最高学历" style="width: 100%">
                <el-option label="本科" value="本科"></el-option>
                <el-option label="硕士" value="硕士"></el-option>
                <el-option label="大专" value="大专"></el-option>
                <el-option label="博士" value="博士"></el-option>
            </el-select>
            </el-form-item>
        </el-col>
        <el-col :span="12">
            <el-form-item label="电话">
            <el-input v-model="form.phone"></el-input>
            </el-form-item>
        </el-col>
        </el-row>

        <!-- 2. 核心经历 (重点修改部分) -->
        <el-divider content-position="left">职业经历</el-divider>
        
        <el-form-item label="工作经验">
        <el-input 
            type="textarea" 
            v-model="form.work_experience" 
            :rows="4" 
            placeholder="请输入您的工作经历，例如：&#10;2020-2022 某某科技 | 前端工程师&#10;负责后台管理系统的开发..."
        ></el-input>
        </el-form-item>

        <el-form-item label="项目经验">
        <el-input 
            type="textarea" 
            v-model="form.project_experience" 
            :rows="4" 
            placeholder="请输入主要项目经验，例如：&#10;电商中台系统：使用Vue3重构，提升性能30%..."
        ></el-input>
        </el-form-item>

        <!-- 3. 其他信息 -->
        <el-divider content-position="left">技能与总结</el-divider>
        
        <el-form-item label="自我评价">
        <el-input 
            type="textarea" 
            v-model="form.summary" 
            :rows="3" 
            placeholder="简短的自我介绍..."
        ></el-input>
        </el-form-item>

    </el-form>

    <template #footer>
        <span class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存简历</el-button>
        </span>
    </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useResumeStore } from '../../../store/resume'
import {
  getResumeListAPI,
  createResumeAPI,
  parseResumeFileAPI,
  deleteResumeAPI,
  setDefaultResumeAPI
} from '../../../api/resume'
import request from '../../../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

// --- Store & State ---
const resumeStore = useResumeStore()
const currentResumeId = computed(() => resumeStore.currentResumeId)

const resumeList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const uploadFile = ref(null)

// 表单数据结构 (需对应数据库字段)
const defaultForm = {
  id: null,
  title: '',
  name: '',
  phone: '',
  email: '',
  education: '',
  school_info: '', // 对应数据库字段
  experience: '',
  work_experience: '',  
  project_experience: '',
  skills: '',
  summary: ''
}
const form = ref({ ...defaultForm })

// --- 方法 ---

// 获取列表
const fetchResumes = async () => {
  try {
    const res = await getResumeListAPI()
    resumeList.value = res || []
  } catch (error) {
    ElMessage.error('加载简历列表失败')
  }
}

// 新建
const handleCreate = () => {
  isEdit.value = false
  form.value = { ...defaultForm } // 重置表单
  dialogVisible.value = true
}

// 编辑
const handleEdit = (resume) => {
  isEdit.value = true
  // 深拷贝对象，防止在弹窗取消时直接修改了列表中的数据
  form.value = JSON.parse(JSON.stringify(resume)) 
  dialogVisible.value = true
}

// 文件上传解析
const handleUploadParse = async (options) => {
  const { file, onSuccess, onError } = options
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await parseResumeFileAPI(fd)
    const data = res.data || res
    Object.assign(form.value, {
      title: data.title || '', name: data.name || '', phone: data.phone || '',
      email: data.email || '', education: data.education || '', experience: data.experience || '',
      skills: Array.isArray(data.skills) ? data.skills.join(', ') : (data.skills || ''),
      summary: data.summary || '', work_experience: data.work_experience || '',
      project_experience: data.project_experience || ''
    })
    ElMessage.success('解析完成，请核对后提交')
    onSuccess(res)
  } catch { ElMessage.error('解析失败'); onError() }
}

// 提交保存
const submitForm = async () => {
  submitLoading.value = true
  try {
    const fd = new FormData()
    fd.append('name', form.value.name || '')
    fd.append('title', form.value.title || '')
    fd.append('phone', form.value.phone || '')
    fd.append('email', form.value.email || '')
    fd.append('education', form.value.education || '')
    fd.append('experience', form.value.experience || '')
    fd.append('skills', JSON.stringify(
      typeof form.value.skills === 'string'
        ? form.value.skills.split(/[,，]/).map(s => s.trim()).filter(s => s)
        : (form.value.skills || [])
    ))
    fd.append('summary', form.value.summary || '')
    fd.append('work_experience', form.value.work_experience || '')
    fd.append('project_experience', form.value.project_experience || '')

    if (isEdit.value) {
      await request.put(`/user/resumes/${form.value.id}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    } else {
      await createResumeAPI(fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchResumes()
  } catch { ElMessage.error('保存失败') }
  finally { submitLoading.value = false }
}

// 选中简历
const selectResume = async (resume) => {
  resumeStore.switchResume(resume.id)
  if (!resume.is_default) {
    await setDefaultResumeAPI(resume.id)
  }
  ElMessage.success(`已切换为 "${resume.title}"`)
  fetchResumes()
}

// 设为默认
const handleSetDefault = async (id) => {
  try {
    await setDefaultResumeAPI(id)
    ElMessage.success('已设为默认简历')
    fetchResumes()
  } catch { ElMessage.error('操作失败') }
}

// 删除
const handleDelete = (id) => {
  ElMessageBox.confirm('确定要删除这份简历吗？此操作无法恢复。', '警告', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteResumeAPI(id)
      ElMessage.success('删除成功')
      fetchResumes()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const statusText = s => ({ pending: '待审核', processed: '待审核', reviewed: '已通过' }[s] || s)
const statusType = s => ({ pending: 'warning', processed: 'warning', reviewed: 'success' }[s] || 'info')

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString()
}

// 初始化
onMounted(() => {
  fetchResumes()
})
</script>

<style scoped>
.resume-manager {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
}

/* 卡片样式 */
.resume-card {
  border: 1px solid #ebeef5;
  transition: all 0.3s;
}

/* 选中状态的高亮样式 */
.resume-card.is-active {
  border-color: #67c23a;
  background-color: #f0f9eb;
  box-shadow: 0 0 15px rgba(103, 194, 58, 0.2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.title {
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.card-body p {
  margin: 8px 0;
  color: #606266;
  font-size: 13px;
  display: flex;
  align-items: center;
}

.card-body i {
  margin-right: 8px;
  color: #909399;
  width: 16px;
}

.card-footer {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 4px;
}
.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>