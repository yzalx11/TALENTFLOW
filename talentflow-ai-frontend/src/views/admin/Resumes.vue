<template>
  <div class="resumes-container">
    <!-- 1. 顶部操作栏 -->
    <div class="header-card">
      <h2>简历数据管理</h2>
      <div class="actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户或技能"
          prefix-icon="Search"
          style="width: 240px; margin-right: 10px"
          @keyup.enter="fetchData"
        />
        <el-button type="primary" @click="openUploadDialog">
          <el-icon><Upload /></el-icon>
          上传简历
        </el-button>
      </div>
    </div>

    <!-- 2. 数据表格 -->
    <el-card shadow="never" class="table-card">
      <el-table
        :data="data"
        v-loading="loading"
        style="width: 100%"
        stripe
        border
      >
        <el-table-column prop="name" label="用户/姓名" width="120" />
        <el-table-column prop="title" label="意向职位" width="180" />
        
        <!-- 技能标签列 -->
        <el-table-column label="技能标签" min-width="180">
          <template #default="scope">
            <el-tag
              v-for="(tag, index) in (scope.row.skills || [])"
              :key="index"
              size="small"
              type="info"
              effect="plain"
              style="margin-right: 4px; margin-bottom: 4px"
            >
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 状态列 -->
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)" effect="light">
              {{ statusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="updatedAt" label="更新时间" width="160" />

        <!-- 操作列 -->
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" size="small" @click="handlePreview(scope.row)">预览</el-button>
            <el-button link type="primary" size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="openReview(scope.row)">审核</el-button>
            <el-popconfirm title="确定删除这份简历吗？" @confirm="handleDelete(scope.row)" width="160">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next, jumper"
          @current-change="fetchData"
          @size-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 3. 简历录入与解析弹窗 -->
    <el-dialog
      v-model="uploadVisible"
      :title="uploadEditId ? '编辑简历' : '简历录入与解析'"
      width="750px"
      top="5vh"
      destroy-on-close
      append-to-body
      @closed="resetUploadForm"
    >
      <el-form :model="uploadForm" :rules="uploadRules" ref="uploadFormRef" label-width="100px" label-position="left">
        <!-- 简历文件上传 + 自动解析 -->
        <el-form-item label="简历解析" v-if="!uploadEditId">
          <el-upload
            class="upload-demo"
            drag
            :auto-upload="true"
            :show-file-list="true"
            :limit="1"
            accept=".pdf,.doc,.docx,.txt"
            :http-request="handleUploadParse"
            :on-remove="handleFileRemove"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处 或 <em>点击上传简历</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 .pdf, .doc, .docx, .txt 格式，上传后将自动解析并填充下方表单</div>
            </template>
          </el-upload>
        </el-form-item>

        <el-divider v-if="!uploadEditId" />

        <!-- 基础信息 -->
        <el-form-item label="姓名" prop="name">
          <el-input v-model="uploadForm.name" placeholder="请输入求职者姓名" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="联系电话" prop="phone">
              <el-input v-model="uploadForm.phone" placeholder="请输入手机号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="uploadForm.email" placeholder="请输入邮箱" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 职位意向 -->
        <el-form-item label="意向职位" prop="title">
          <el-input v-model="uploadForm.title" placeholder="例如：前端开发工程师" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学历">
              <el-input v-model="uploadForm.education" placeholder="如：本科" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工作年限">
              <el-input v-model="uploadForm.experience" placeholder="如：3年" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 详细内容 -->
        <el-form-item label="个人简介">
          <el-input v-model="uploadForm.summary" type="textarea" :rows="3" placeholder="请简要描述个人优势或自我评价" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="工作经历">
          <el-input v-model="uploadForm.work_experience" type="textarea" :rows="4" placeholder="请描述主要工作经历" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="项目经验">
          <el-input v-model="uploadForm.project_experience" type="textarea" :rows="4" placeholder="请描述主要项目经历" maxlength="1000" show-word-limit />
        </el-form-item>

        <!-- 技能标签 -->
        <el-form-item label="技能标签">
          <el-select
            v-model="uploadForm.skills"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入技能后回车添加"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploadLoading" @click="submitUploadForm">
          {{ uploadEditId ? '保存修改' : '立即录入' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 4. 简历预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      :title="currentResume?.name + ' 的简历详情'"
      width="650px"
      destroy-on-close
      class="preview-dialog"
    >
      <div v-if="currentResume" class="resume-detail-view">
        <div class="resume-header">
          <div class="user-info">
            <h3 class="name">{{ currentResume.name }}</h3>
            <span class="job-title" v-if="currentResume.title">{{ currentResume.title }}</span>
          </div>
          <div class="status-badge">
            <el-tag :type="statusTagType(currentResume.status)">
              {{ statusLabel(currentResume.status) }}
            </el-tag>
          </div>
        </div>
        <el-divider />
        <el-descriptions :column="2" size="small" border class="mb-4">
          <el-descriptions-item label="联系电话">{{ currentResume.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ currentResume.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ currentResume.education || '-' }}</el-descriptions-item>
          <el-descriptions-item label="工作年限">{{ currentResume.experience || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="section" v-if="currentResume.skills?.length">
          <h4 class="section-title">技能</h4>
          <div class="tags-wrapper">
            <el-tag v-for="(skill, index) in currentResume.skills" :key="index" type="primary" effect="plain" style="margin-right: 8px; margin-bottom: 8px;">
              {{ skill }}
            </el-tag>
          </div>
        </div>
        <div class="section" v-if="currentResume.summary">
          <h4 class="section-title">个人简介</h4>
          <p class="bio-text">{{ currentResume.summary }}</p>
        </div>
        <div class="section" v-if="currentResume.project_experience">
          <h4 class="section-title">项目经验</h4>
          <p class="bio-text">{{ currentResume.project_experience }}</p>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="previewVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 审核弹窗 -->
    <el-dialog v-model="reviewVisible" title="审核简历" width="900px" top="3vh" destroy-on-close>
      <div v-if="reviewResume" class="review-layout">
        <div class="review-left">
          <h4 class="section-title">简历原文</h4>
          <div class="raw-text-box"><pre>{{ reviewResume.raw_text || '无文本内容' }}</pre></div>
        </div>
        <div class="review-right">
          <h4 class="section-title">AI 提取技能</h4>
          <div class="tags-wrap">
            <el-tag v-for="sk in reviewSkills" :key="sk.id" closable type="primary" effect="plain" style="margin:2px 4px" @close="removeReviewSkill(sk.id)">{{ sk.standard_name }}</el-tag>
            <span v-if="!reviewSkills.length" class="text-muted">无技能</span>
          </div>
          <el-divider />
          <h4 class="section-title">从标准库添加</h4>
          <el-select v-model="selectedSkillId" filterable remote :remote-method="searchSkills" placeholder="搜索技能" style="width:100%" @change="addReviewSkill">
            <el-option v-for="sk in allSkills" :key="sk.id" :label="sk.standard_name + ' (' + (sk.category||'') + ')'" :value="sk.id" />
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="reviewLoading" @click="submitReview">保存审核</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Search, Upload, UploadFilled } from '@element-plus/icons-vue';
import axios from '../../utils/request';

// --- 表格数据状态 ---
const data = ref([]);
const loading = ref(false);
const searchQuery = ref('');
const statusFilter = ref('');

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
});

// --- 上传弹窗 ---
const uploadVisible = ref(false);
const uploadLoading = ref(false);
const uploadFormRef = ref(null);
const uploadEditId = ref(null);  // 编辑模式时有值
const uploadForm = reactive({
  name: '', title: '', phone: '', email: '', education: '', experience: '',
  summary: '', work_experience: '', project_experience: '', skills: [], file: null, raw_text: ''
});
const uploadRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入联系电话', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }],
  title: [{ required: true, message: '请输入意向职位', trigger: 'blur' }],
};

// --- 预览弹窗 ---
const previewVisible = ref(false);
const currentResume = ref(null);

// (编辑状态已合并到 uploadEditId)

// --- 辅助函数 ---
const statusLabel = (s) => ({ pending: '待处理', processed: '已提取', reviewed: '已审核', Active: '已激活', Pending: '待审核' }[s] || s)
const statusTagType = (s) => ({ pending: 'warning', processed: 'info', reviewed: 'success', Active: 'success', Pending: 'warning' }[s] || 'info')

const mapResumeData = (item) => {
  return {
    id: item.id,
    // 【修正】后端返回的是 name
    name: item.name, 
    // 【修正】后端返回的是 title
    title: item.title, 
    phone: item.phone,
    email: item.email,
    education: item.education,
    // 确保这些字段后端也有返回
    summary: item.summary || '',
    project_experience: item.project_experience || '',
    work_experience: item.work_experience || '',
    skills: item.skills || [],
    status: item.status,
    updatedAt: item.updated_at
  };
};
// const mapResumeData = (item) => {
//   return {
//     id: item.id,
//     userName: item.name,
//     jobTitle: item.title,
//     phone: item.phone,
//     email: item.email,
//     education: item.education,
//     experience: '未知',
//     skills: item.skills || [],
//     status: item.status,
//     updatedAt: item.created_at,
//     bio: item.summary,
//     projectExperience: item.project_experience
//   };
// };

// --- 业务逻辑 ---

const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get('/admin/resumes', {
      params: {
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        keyword: searchQuery.value || undefined,
        status: statusFilter.value || undefined,
      }
    });
    const resData = response;
    data.value = (resData.items || []).map(mapResumeData);
    pagination.total = resData.total || 0;
  } catch (error) {
    ElMessage.error('获取简历列表失败');
  } finally {
    loading.value = false;
  }
};

const handlePreview = async (row) => {
  try {
    const response = await axios.get(`/admin/resumes/${row.id}`);
    currentResume.value = mapResumeData(response);
    previewVisible.value = true;
  } catch (error) {
    ElMessage.error('获取简历详情失败');
  }
};

const handleDelete = async (row) => {
  try {
    await axios.delete(`/admin/resumes/${row.id}`);
    ElMessage.success('删除成功');
    fetchData();
  } catch (error) {
    ElMessage.error('删除失败');
  }
};

// 上传 + 解析 + 表单提交
const initialUploadForm = { name: '', title: '', phone: '', email: '', education: '', experience: '', summary: '', work_experience: '', project_experience: '', skills: [], file: null, raw_text: '' }

const resetUploadForm = () => {
  uploadEditId.value = null
  Object.assign(uploadForm, { ...initialUploadForm, skills: [] })
  uploadFormRef.value?.resetFields()
}

const openUploadDialog = () => {
  resetUploadForm()
  uploadVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  uploadEditId.value = row.id
  const mapped = mapResumeData(row)
  Object.assign(uploadForm, {
    name: mapped.name || '', title: mapped.title || '', phone: mapped.phone || '',
    email: mapped.email || '', education: mapped.education || '', experience: mapped.experience || '',
    summary: mapped.summary || '', work_experience: mapped.work_experience || '',
    project_experience: mapped.project_experience || '', skills: [...(mapped.skills || [])],
    file: null
  })
  uploadVisible.value = true
}

// 文件上传 → 调用 /parse 自动填表
const handleUploadParse = async (options) => {
  const { file, onSuccess, onError } = options
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await axios.post('/admin/resumes/parse', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const data = res.data || res
    Object.assign(uploadForm, {
      name: data.name || '', title: data.title || '', phone: data.phone || '',
      email: data.email || '', education: data.education || '', experience: data.experience || '',
      summary: data.summary || '', work_experience: data.work_experience || '',
      project_experience: data.project_experience || '', skills: data.skills || [],
      raw_text: res.raw_text || ''
    })
    ElMessage.success('解析完成！请核对下方信息后提交')
    onSuccess(res)
  } catch (e) {
    ElMessage.error('文件解析失败')
    onError(e)
  }
}

const handleFileRemove = () => {
  uploadForm.file = null
}

// 提交表单（新增 or 编辑）
const submitUploadForm = async () => {
  if (!uploadFormRef.value) return
  await uploadFormRef.value.validate(async (valid) => {
    if (!valid) return
    uploadLoading.value = true
    try {
      const fd = new FormData()
      fd.append('name', uploadForm.name)
      fd.append('title', uploadForm.title || '')
      fd.append('phone', uploadForm.phone || '')
      fd.append('email', uploadForm.email || '')
      fd.append('education', uploadForm.education || '')
      fd.append('experience', uploadForm.experience || '')
      fd.append('skills', JSON.stringify(uploadForm.skills || []))
      fd.append('summary', uploadForm.summary || '')
      fd.append('work_experience', uploadForm.work_experience || '')
      fd.append('project_experience', uploadForm.project_experience || '')
      fd.append('raw_text', uploadForm.raw_text || '')

      if (uploadEditId.value) {
        await axios.put(`/admin/resumes/${uploadEditId.value}`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        ElMessage.success('更新成功')
      } else {
        await axios.post('/admin/resumes', fd, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        ElMessage.success('录入成功')
      }
      uploadVisible.value = false
      fetchData()
    } catch (e) {
      ElMessage.error(uploadEditId.value ? '更新失败' : '录入失败')
    } finally {
      uploadLoading.value = false
    }
  })
}

// --- 审核 ---
const reviewVisible = ref(false); const reviewLoading = ref(false)
const reviewResume = ref(null); const reviewSkills = ref([])
const allSkills = ref([]); const selectedSkillId = ref(null)

const openReview = async (row) => {
  try {
    const res = await axios.get(`/admin/resumes/${row.id}`)
    const d = res.data || res
    reviewResume.value = d
    reviewSkills.value = [...(d.standard_skills || d.skills || [])]
    allSkills.value = d.all_skills || []
    reviewVisible.value = true
  } catch { ElMessage.error('加载失败') }
}
const removeReviewSkill = (id) => { reviewSkills.value = reviewSkills.value.filter(s => s.id !== id) }
const addReviewSkill = (id) => {
  if (!id) return
  if (reviewSkills.value.find(s => s.id === id)) return
  const sk = allSkills.value.find(s => s.id === id)
  if (sk) reviewSkills.value.push(sk)
  selectedSkillId.value = null
}
const searchSkills = async (q) => {
  if (!q) return
  const r = await axios.get('/admin/skills', { params: { q, limit: 30 } })
  allSkills.value = r.data || r
}
const submitReview = async () => {
  reviewLoading.value = true
  try {
    await axios.post(`/admin/resumes/${reviewResume.value.id}/review`, {
      skill_ids: reviewSkills.value.map(s => s.id)
    })
    ElMessage.success('审核完成')
    reviewVisible.value = false; fetchData()
  } catch { ElMessage.error('审核失败') }
  finally { reviewLoading.value = false }
}

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
/* 保持原有样式不变 */
.resumes-container { padding: 20px; background-color: #f5f7fa; min-height: 100vh; }
.header-card { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.header-card h2 { margin: 0; font-size: 18px; font-weight: 600; color: #303133; }
.table-card { border-radius: 8px; }
.pagination-container { margin-top: 20px; display: flex; justify-content: flex-end; }
.resume-detail-view { padding: 10px; }
.resume-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.resume-header .name { margin: 0; font-size: 20px; color: #303133; }
.resume-header .job-title { font-size: 14px; color: #606266; margin-top: 4px; display: block; }
.section { margin-top: 15px; }
.section-title { font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 10px; border-left: 4px solid #409EFF; padding-left: 8px; }
.bio-text { font-size: 13px; color: #606266; line-height: 1.6; background: #f9f9f9; padding: 10px; border-radius: 4px; }
.mb-4 { margin-bottom: 16px; }
.upload-demo { width: 100%; }
:deep(.el-upload-dragger) { width: 100%; padding: 20px; }
.review-layout { display: flex; gap: 20px; height: 400px; }
.review-left { flex: 1; overflow: auto; }
.review-right { flex: 1; overflow: auto; }
.raw-text-box { background: #fafafa; border: 1px solid #ebeef5; border-radius: 6px; padding: 12px; max-height: 350px; overflow: auto; }
.raw-text-box pre { white-space: pre-wrap; word-break: break-all; font-size: 13px; color: #606266; margin: 0; }
.tags-wrap { min-height: 30px; }
</style>