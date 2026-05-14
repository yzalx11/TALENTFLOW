<template>
  <div class="job-list">
    <el-card class="search-card">
      <el-input
        v-model="searchQuery"
        placeholder="搜索职位名称或公司"
        style="width: 300px"
        clearable
        @clear="fetchData"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" @click="fetchData">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        录入新职位
      </el-button>
      <el-button type="success" @click="handleBatchImport">
        <el-icon><Upload /></el-icon>
        批量导入职位
      </el-button>
    </el-card>

    <el-card class="table-card">
      <el-table :data="data" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="职位名称" min-width="180" />
        <el-table-column prop="company" label="公司" width="150" />
        <el-table-column prop="salary" label="薪资" width="120" />
        <el-table-column prop="location" label="工作地点" width="120" />
        <el-table-column prop="experience_requirement" label="经验要求" width="120" />
        <el-table-column prop="education_requirement" label="学历要求" width="120" />
        <el-table-column label="技能要求" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="skill in parseSkills(row.required_skills)"
              :key="skill"
              type="info"
              size="small"
              style="margin-right: 4px; margin-bottom: 4px"
            >
              {{ skill }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="职位文件" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.file_path"
              type="primary"
              link
              size="small"
              @click="handleViewFile(row.file_path)"
            >
              查看PDF
            </el-button>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" @click="handleEdit(scope.row)">
              编辑
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(scope.row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="职位名称" prop="title">
          <el-input v-model="form.title" placeholder="如：高级前端工程师" />
        </el-form-item>
        
        <el-form-item label="公司" prop="company">
          <el-input v-model="form.company" placeholder="如：字节跳动" />
        </el-form-item>

        <el-form-item label="薪资范围" prop="salary">
          <el-input v-model="form.salary" placeholder="如：25k-40k" />
        </el-form-item>

        <el-form-item label="工作地点" prop="location">
          <el-input v-model="form.location" placeholder="如：北京" />
        </el-form-item>

        <el-form-item label="经验要求" prop="experience_requirement">
          <el-input v-model="form.experience_requirement" placeholder="如：3-5年" />
        </el-form-item>

        <el-form-item label="学历要求" prop="education_requirement">
          <el-input v-model="form.education_requirement" placeholder="如：本科" />
        </el-form-item>

        <el-form-item label="技能要求" prop="skills">
          <el-input 
            v-model="form.skills" 
            placeholder="请输入技能，用逗号分隔 (如：Vue3, TS, Webpack)" 
          />
        </el-form-item>

        <el-form-item label="职位描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="请输入职位描述..."
          />
        </el-form-item>

        <el-form-item label="招聘PDF">
          <el-upload
            class="upload-demo"
            drag
            action="#" 
            :auto-upload="false"
            :limit="1"
            :file-list="fileList"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            accept=".pdf"
            v-loading="uploadLoading"
            element-loading-text="AI正在拼命解析中..."
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽 PDF 文件或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                上传后将自动识别内容并填入上方表单
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search, UploadFilled } from '@element-plus/icons-vue';
import axios from '../../utils/request';

// --- 状态定义 ---
const data = ref([]);
const loading = ref(false);
const uploadLoading = ref(false); // 专门用于上传解析的loading动画
const searchQuery = ref('');

// 弹窗相关
const dialogVisible = ref(false);
const dialogTitle = ref('录入新职位');
const formRef = ref(null);
const selectedFile = ref(null);
const fileList = ref([]);
const isEdit = ref(false);

// --- 修复1 & 修复2：补全表单初始值字段 ---
const initialForm = {
  id: null,
  title: '',
  company: '',
  salary: '', // 统一使用 salary
  location: '',
  experience_requirement: '',
  education_requirement: '',
  skills: '', 
  description: '',
  file_path: '' 
};

const form = reactive({ ...initialForm });

const rules = reactive({
  title: [{ required: true, message: '请输入职位名称', trigger: 'blur' }],
  company: [{ required: true, message: '请输入公司名称', trigger: 'blur' }],
  skills: [
    {
      required: true,
      validator: (rule, value, callback) => {
        if (!value || value.trim() === '') {
          callback(new Error('请输入或选择至少一项技能'));
          return;
        }
        callback();
      },
      trigger: ['blur', 'change']
    }
  ]
})

const parseSkills = (skills) => {
  if (!skills) return [];
  if (Array.isArray(skills)) return skills;
  try {
    return JSON.parse(skills);
  } catch (e) {
    return [skills];
  }
};

const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get('admin/jobs', {
      params: { keyword: searchQuery.value } 
    });
    data.value = response.data || response;
  } catch (error) {
    ElMessage.error('获取职位列表失败');
  } finally {
    loading.value = false;
  }
};

// --- 修复3：合并两个 handleFileChange，实现既绑定文件，又触发预解析 ---
// --- 修复：兼容 axios 拦截器数据解包的 handleFileChange ---
// --- 修复：兼容 axios 拦截器，并增加默认值兜底的 handleFileChange ---
const handleFileChange = async (file, uploadFileList) => {
  selectedFile.value = file.raw; 
  fileList.value = uploadFileList;
  if (!file.raw) return;
  
  const formData = new FormData();
  formData.append('file', file.raw);
  
  try {
    uploadLoading.value = true;
    const res = await axios.post('admin/jobs/parse', formData);
    console.log("【调试】AI解析接口返回的数据:", res); 

    // ✅ 修复：兼容两种axios拦截器情况，直接拿到正确的aiData
    let aiData;
    if (res.success && res.data) {
      // 拦截器已解包：res = {success: true, data: {...}}
      aiData = res.data;
    } else if (res.data && res.data.success && res.data.data) {
      // 拦截器未解包：res.data = {success: true, data: {...}}
      aiData = res.data.data;
    } else {
      throw new Error("后端返回格式错误");
    }

    // 字段默认值兜底
    aiData.title = aiData.title || `解析职位-${file.name.split('.')[0]}`;
    aiData.company = aiData.company || '未知公司';
    aiData.salary = aiData.salary || '面议';
    aiData.location = aiData.location || '不限';
    aiData.experience_requirement = aiData.experience_requirement || '不限';
    aiData.education_requirement = aiData.education_requirement || '不限';

    // 自动填充表单
    Object.assign(form, aiData);

    // 处理技能数组转字符串
    if (Array.isArray(aiData.required_skills)) {
      form.skills = aiData.required_skills.join(', ');
    } else if (typeof aiData.required_skills === 'string') {
      form.skills = aiData.required_skills;
    }

    ElMessage.success('✨ AI 已成功解析文档并自动填充表单！');
  } catch (error) {
    console.error("解析报错:", error)
    ElMessage.warning('自动解析响应失败，请检查后端服务');
  } finally {
    uploadLoading.value = false;
  }
};

const handleFileRemove = () => {
  selectedFile.value = null;
  fileList.value = [];
};

const handleViewFile = (filePath) => {
  window.open(filePath, '_blank');
};

const handleEdit = (row) => {
  Object.assign(form, row);
  
  // 处理技能标签显示
  if (Array.isArray(row.required_skills)) {
    form.skills = row.required_skills.join(', ');
  } else if (typeof row.required_skills === 'string') {
    form.skills = row.required_skills;
  }

  if (row.file_path) {
    fileList.value = [{ name: '已上传文件.pdf', url: row.file_path }];
  } else {
    fileList.value = [];
  }

  dialogTitle.value = '编辑职位';
  isEdit.value = true;
  dialogVisible.value = true;
};

const handleCreate = () => {
  Object.assign(form, initialForm);
  fileList.value = [];
  selectedFile.value = null;
  dialogTitle.value = '录入新职位';
  isEdit.value = false;
  dialogVisible.value = true;
};

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除职位 "${row.title}" 吗？`,
    '警告',
    {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger'
    }
  ).then(async () => {
    try {
      await axios.delete(`admin/jobs/${row.id}`);
      ElMessage.success('删除成功');
      fetchData();
    } catch (error) {
      ElMessage.error('删除失败');
    }
  }).catch(() => {});
};

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields();
  }
  Object.assign(form, initialForm);
  fileList.value = [];
  selectedFile.value = null;
};

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      const formData = new FormData()
      
      // 字段非空处理（避免undefined）
      formData.append('title', form.title.trim() || '')
      formData.append('company', form.company.trim() || '')
      formData.append('salary', form.salary ? form.salary.trim() : '')
      formData.append('location', form.location ? form.location.trim() : '')
      formData.append('experience_requirement', form.experience_requirement ? form.experience_requirement.trim() : '')
      formData.append('education_requirement', form.education_requirement ? form.education_requirement.trim() : '')
      formData.append('description', form.description ? form.description.trim() : '')

      // 安全处理技能列表（兼容中英文逗号）
      let finalSkills = []
      if (typeof form.skills === 'string' && form.skills.trim()) {
        finalSkills = form.skills.split(/[,，]/).map(s => s.trim()).filter(s => s)
        finalSkills = [...new Set(finalSkills)] // 去重
      }
      formData.append('required_skills', JSON.stringify(finalSkills))

      // 追加文件（如果有）
      if (selectedFile.value) {
        formData.append('file', selectedFile.value)
      }

      try {
        // 增加请求超时（处理大文件/慢服务）
        const axiosConfig = { timeout: 60000 }
        if (isEdit.value) {
          await axios.put(`admin/jobs/${form.id}`, formData, axiosConfig)
          ElMessage.success('职位更新成功')
        } else {
          await axios.post('admin/jobs', formData, axiosConfig)
          ElMessage.success('职位创建成功')
        }
        dialogVisible.value = false
        fetchData()
      } catch (error) {
        console.error("提交失败详情:", error)
        // 分场景提示错误
        if (error.response) {
          // 后端返回500，展示具体错误
          ElMessage.error(`提交失败: ${error.response.data.detail || '服务器内部错误'}`)
        } else if (error.request) {
          // 连接被重置（后端崩溃/超时）
          ElMessage.error('提交失败: 服务器连接中断，请检查后端服务')
        } else {
          ElMessage.error(`提交失败: ${error.message}`)
        }
      }
    }
  })
}

const handleBatchImport = () => {
  ElMessage.info('批量导入功能正在开发中，敬请期待！');
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.job-list {
  padding: 20px;
}
.search-card {
  margin-bottom: 20px;
}
.table-card {
  margin-bottom: 20px;
}
.text-muted {
  color: #999;
  font-size: 12px;
}
</style>