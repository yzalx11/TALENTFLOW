<template>
  <div class="job-list">
    <!-- 搜索和操作栏 -->
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

    <!-- 表格 -->
    <el-card class="table-card">
      <el-table :data="data" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="职位名称" min-width="180" />
        <el-table-column prop="company" label="公司" width="150" />
        <el-table-column prop="salary_range" label="薪资" width="120" />
        
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

    <!-- 编辑/新增弹窗 -->
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

        <el-form-item label="薪资范围" prop="salary_range">
          <el-input v-model="form.salary_range" placeholder="如：25k-40k" />
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

        <!-- 文件上传组件 -->
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
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽 PDF 文件或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                上传的 PDF 将被解析并存入向量数据库用于 AI 匹配
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
import axios from '../../utils/request'; // 确保你的 axios 实例配置正确

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

// --- 表单初始值 ---
const initialForm = {
  id: null,
  title: '',
  company: '',
  salary_range: '',
  skills: '', // 这里存字符串，提交时转数组
  description: '',
  file_path: '' // 如果是编辑模式，可能已经有文件路径
};

const form = reactive({ ...initialForm });

// 校验规则
const rules = {
  title: [{ required: true, message: '请输入职位名称', trigger: 'blur' }],
  company: [{ required: true, message: '请输入公司名称', trigger: 'blur' }],
  salary_range: [{ required: true, message: '请输入薪资范围', trigger: 'blur' }]
};

// --- 辅助函数 ---
// 将后端返回的 JSON 数组或字符串转为数组，方便 el-tag 循环
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
    // 修改点：将参数名改为 keyword，与后端 read_jobs(keyword: str) 对应
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

// --- API 请求 ---
// const fetchData = async () => {
//   loading.value = true;
//   try {
//     // 假设后端接口支持 ?q= 查询
//     const response = await axios.get('admin/jobs', {
//       params: { q: searchQuery.value }
//     });
//     data.value = response.data || response; // 根据实际返回结构调整
//   } catch (error) {
//     ElMessage.error('获取职位列表失败');
//   } finally {
//     loading.value = false;
//   }
// };

// --- 文件处理 ---
const handleFileChange = (file, uploadFileList) => {
  selectedFile.value = file.raw; // 获取原始文件对象
  fileList.value = uploadFileList;
};

const handleFileRemove = () => {
  selectedFile.value = null;
  fileList.value = [];
};

const handleViewFile = (filePath) => {
  // 根据后端返回的文件路径逻辑，可能是直接打开，也可能是下载
  window.open(filePath, '_blank');
};

// --- 事件处理 ---
const handleEdit = (row) => {
  Object.assign(form, row);
  
  // 处理技能标签显示 (如果是数组转字符串)
  if (Array.isArray(row.skills)) {
    form.skills = row.skills.join(', ');
  }

  // 处理文件列表回显
  if (row.file_path) {
    fileList.value = [
      { name: '已上传文件.pdf', url: row.file_path }
    ];
  } else {
    fileList.value = [];
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

            // 10. 添加文件（如果选择了新文件）
            if (selectedFile.value) {
                formData.append('file', selectedFile.value);
            }

            try {
                if (form.id) {
                    // 编辑模式（PUT）
                    // 注意：这里假设你的 PUT 接口路径 is `/admin/jobs/${form.id}`
                    await axios.put(`/admin/jobs/${form.id}`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                    });
                    ElMessage.success('更新成功');
                } else {
                    // 新增模式（POST）
                    await axios.post('/admin/jobs', formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                    });
                    ElMessage.success('创建成功');
                }
                dialogVisible.value =false;
                fetchData();
            } catch (err) {
                ElMessage.error(err.response?.data?.detail || '提交失败');
            }
        }
    });
};

const handleBatchImport = () => {
  // 目前先做一个 UI 占位提示，后续在这里打开上传弹窗
  ElMessage.info('批量导入功能正在开发中，敬请期待！');
  
  // 后续开发计划：
  // 1. dialogBatchVisible.value = true; (打开专门的导入弹窗)
  // 2. 弹窗内放入 <el-upload> 组件，支持拖拽多个文件
  // 3. 提交给后端的 /api/v1/admin/jobs/batch-import 接口
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