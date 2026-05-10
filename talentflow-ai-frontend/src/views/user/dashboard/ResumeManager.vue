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
            <el-tag v-if="resume.is_default" type="success" size="small">默认</el-tag>
          </div>
          
          <div class="card-body">
            <p><i class="el-icon-user"></i> {{ resume.name || '未填写姓名' }}</p>
            <p><i class="el-icon-phone"></i> {{ resume.phone || '未填写电话' }}</p>
            <p><i class="el-icon-date"></i> 更新: {{ formatDate(resume.updated_at) }}</p>
          </div>

          <div class="card-footer">
            <el-button 
              v-if="resume.id !== currentResumeId"
              type="success" 
              size="small" 
              @click="selectResume(resume)"
            >
              选中
            </el-button>
            <el-tag v-else type="success" size="small">当前选中</el-tag>

            <el-button size="small" @click="handleEdit(resume)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(resume.id)">删除</el-button>
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
  updateResumeAPI, 
  deleteResumeAPI 
} from '../../../api/resume' // 请根据实际路径调整
import { ElMessage, ElMessageBox } from 'element-plus'

// --- Store & State ---
const resumeStore = useResumeStore()
const currentResumeId = computed(() => resumeStore.currentResumeId)

const resumeList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)

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

// 提交保存
const submitForm = () => {
  submitLoading.value = true
  
  const apiCall = isEdit.value 
    ? updateResumeAPI(form.value.id, form.value)
    : createResumeAPI(form.value)

  apiCall
    .then(() => {
      ElMessage.success('保存成功')
      dialogVisible.value = false
      fetchResumes()
    })
    .catch(() => {
      ElMessage.error('保存失败，请检查网络')
    })
    .finally(() => {
      submitLoading.value = false
    })
}

// 选中简历
const selectResume = (resume) => {
  resumeStore.setCurrentResume(resume.id)
  ElMessage.success(`已选中 "${resume.title}" 用于投递`)
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
  border-top: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>