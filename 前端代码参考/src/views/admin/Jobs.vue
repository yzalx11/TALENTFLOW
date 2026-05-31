<template>
  <div class="job-list">
    <!-- 搜索和操作栏 -->
    <el-card class="search-card">
      <el-input
        v-model="searchQuery"
        placeholder="搜索职位名称、公司或地点"
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
    </el-card>

    <!-- 表格 -->
    <el-card class="table-card">
      <el-table
        :data="data"
        v-loading="loading"
        border
        stripe
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="职位名称" min-width="180" />
        <el-table-column prop="company" label="公司" width="150" />
        
        <!-- 1. 新增：表格列显示地点 -->
        <el-table-column prop="location" label="工作地点" width="120">
          <template #default="{ row }">
            {{ row.location || '不限' }}
          </template>
        </el-table-column>
        
        <el-table-column prop="salary" label="薪资" width="120" />
        
        <!-- 技能要求展示 -->
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
        
        <!-- 职位文件链接 -->
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
        
        <!-- 操作按钮 -->
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="handleEdit(scope.row)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑/新增弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
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
        
        <!-- 2. 新增：地点输入框 -->
        <el-form-item label="工作地点" prop="location">
          <el-input v-model="form.location" placeholder="如：深圳、远程" />
        </el-form-item>

        <el-form-item label="薪资范围" prop="salary">
          <el-input v-model="form.salary" placeholder="如：25k-40k" />
        </el-form-item>

        <!-- 3. 新增：经验与学历要求 -->
        <el-form-item label="经验要求" prop="experience_requirement">
          <el-input v-model="form.experience_requirement" placeholder="如：3-5年" />
        </el-form-item>
        
        <el-form-item label="学历要求" prop="education_requirement">
          <el-input v-model="form.education_requirement" placeholder="如：本科" />
        </el-form-item>

        <el-form-item label="技能要求" prop="required_skills">
          <el-input
            v-model="form.required_skills"
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
        
        <!-- 文件上传组件 -->
        <el-form-item label="招聘文档">
          <el-upload
            class="upload-demo"
            :auto-upload="true"
            :show-file-list="true"
            :http-request="handleUploadParse"
            :on-remove="handleFileRemove"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                上传的文件将被解析并存入向量数据库用于 AI 匹配
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
import axios from '../../utils/request'; // 确保路径正确

// --- 状态定义 ---
const data = ref([]);
const loading = ref(false);
const searchQuery = ref('');

// 弹窗相关
const dialogVisible = ref(false);
const dialogTitle = ref('录入新职位');
const formRef = ref(null);
const selectedFile = ref(null); // 存储选中的文件对象
const fileList = ref([]); // el-upload 需要的文件列表

// --- 表单初始值 (更新：添加新字段) ---
const initialForm = {
  id: null,
  job_id: '', // 默认为空，用户不填就不传
  title: '',
  company: '',
  salary: '',
  // 4. 新增：初始化新字段
  location: '',
  experience_requirement: '',
  education_requirement: '',
  required_skills: '', // 字符串格式，提交时转数组
  description: '',
  file_path: ''
};

const form = reactive({ ...initialForm });

// --- 校验规则 (更新：添加新字段规则) ---
const rules = {
  title: [{ required: true, message: '请输入职位名称', trigger: 'blur' }],
  company: [{ required: true, message: '请输入公司名称', trigger: 'blur' }],
  salary: [{ required: true, message: '请输入薪资范围', trigger: 'blur' }],
  // 5. 新增：为新字段添加必填规则
  location: [{ required: true, message: '请输入工作地点', trigger: 'blur' }],
  experience_requirement: [{ required: true, message: '请输入经验要求', trigger: 'blur' }],
  education_requirement: [{ required: true, message: '请输入学历要求', trigger: 'blur' }]
};

// --- 辅助函数 ---
// 将后端返回的 JSON 字符串或数组转为数组，方便 el-tag 循环
const parseSkills = (skills) => {
  if (!skills) return [];
  if (Array.isArray(skills)) return skills;
  try {
    return JSON.parse(skills);
  } catch (e) {
    return [skills];
  }
};

// --- API 请求 ---
const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get('admin/jobs', { params: { keyword: searchQuery.value } });
    data.value = response.data || response;
  } catch (error) {
    ElMessage.error('获取职位列表失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

// --- 文件处理 ---
const handleFileRemove = () => {
  selectedFile.value = null;
  fileList.value = [];
};

const handleViewFile = (filePath) => {
  if (!filePath) return;
  window.open(filePath, '_blank');
};

// --- 事件处理 ---
const handleEdit = (row) => {
  // 重置表单状态
  Object.assign(form, initialForm);
  fileList.value = [];
  selectedFile.value = null;
  
  // 填充数据
  Object.assign(form, row);
  
  // 处理技能标签显示 (数组转字符串)
  if (Array.isArray(row.required_skills)) {
    form.required_skills = row.required_skills.join(', ');
  }
  
  // 处理文件列表回显 (显示真实文件名)
  if (row.file_path) {
    const fileName = row.file_path.split('/').pop() || '已上传文件';
    fileList.value = [{ name: fileName, url: row.file_path }];
  }
  dialogTitle.value = '编辑职位';
  dialogVisible.value = true;
};

const handleCreate = () => {
  Object.assign(form, initialForm);
  fileList.value = [];
  selectedFile.value = null;
  dialogTitle.value = '录入新职位';
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
      console.error(error);
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

// --- 新增：用于拦截上传并解析的函数 ---
const parsing = ref(false); // 标记是否正在解析中
const handleUploadParse = async ({ file, onSuccess, onError }) => {
  const formData = new FormData();
  formData.append('file', file);
  try {
    parsing.value = true;
    const response = await axios.post('admin/jobs/parse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    const parsedData = response; // 假设 response.data 是解析出的对象

    // 6. 新增：填充 AI 解析出的新字段
    form.title = parsedData.title || form.title;
    form.company = parsedData.company || form.company;
    form.salary = parsedData.salary || form.salary;
    form.location = parsedData.location || form.location;
    form.experience_requirement = parsedData.experience_requirement || form.experience_requirement;
    form.education_requirement = parsedData.education_requirement || form.education_requirement;
    form.description = parsedData.description || form.description;

    // 7. 技能标签处理：数组转字符串
    if (parsedData.required_skills && Array.isArray(parsedData.required_skills)) {
      form.required_skills = parsedData.required_skills.join(', ');
    }
    ElMessage.success('PDF 解析成功，表单已自动填充，请检查');

    // 标记文件已解析，不再走常规的 submit 流程上传文件
    selectedFile.value = null; // 阻止 handleSubmit 再次上传
    fileList.value = [{ name: file.name, url: '#' }]; // 仅用于 UI 显示
    onSuccess(response);
  } catch (error) {
    ElMessage.error('PDF解析失败，请手动填写或检查文件格式');
    onError(error);
  } finally {
    parsing.value = false;
  }
};

// --- 提交处理 ---
const handleSubmit = () => {
  if (!formRef.value) return;
  formRef.value.validate(async (valid) => {
    if (valid) {
      const formData = new FormData();
      
      // 8. 新增：添加新字段到提交数据中
      formData.append('title', form.title);
      formData.append('company', form.company);
      formData.append('salary', form.salary); // 注意：后端字段名为 salary_range
      formData.append('location', form.location);
      formData.append('experience_requirement', form.experience_requirement);
      formData.append('education_requirement', form.education_requirement);
      formData.append('description', form.description);

      // 9. 处理技能数组
      const skillsArr = form.required_skills
        .split(',')
        .map(s => s.trim())
        .filter(s => s);
      formData.append('required_skills', JSON.stringify(skillsArr));

      // 10. 添加文件 (如果选择了新文件)
      if (selectedFile.value) {
        formData.append('file', selectedFile.value);
      }

      try {
        if (form.id) {
          // 编辑模式 (PUT)
          // 注意：这里假设你的 PUT 接口路径是 `/admin/jobs/${form.id}`
          await axios.put(`admin/jobs/${form.id}`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          ElMessage.success('更新成功');
        } else {
          // 新增模式 (POST)
          await axios.post('admin/jobs', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          ElMessage.success('创建成功');
        }
        dialogVisible.value = false;
        fetchData();
      } catch (error) {
        console.error(error);
        ElMessage.error('操作失败，请检查后端日志');
      }
    }
  });
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
.text-muted {
  color: #999;
  font-size: 13px;
}
</style>