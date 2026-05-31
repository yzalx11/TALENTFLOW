<template>
  <div class="task-management">
    <div class="header-actions mb-4">
      <el-button type="primary" @click="handleCreate">发布新任务</el-button>
      <el-input v-model="searchQuery" placeholder="搜索任务标题..." style="width:240px;margin-left:10px" @keyup.enter="fetchTasks" clearable @clear="fetchTasks" />
    </div>

    <el-table :data="taskList" stripe v-loading="loading" style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="任务标题" min-width="180" />
      <el-table-column prop="category" label="分类" width="80" />
      <el-table-column label="赏金" width="100">
        <template #default="s">¥{{ s.row.price }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="s">
          <el-tag :type="statusTag(s.row.status)" size="small">{{ statusLabel(s.row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="difficulty" label="难度" width="80" />
      <el-table-column label="接单人" width="100">
        <template #default="s">{{ s.row.taken_by_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="接单时间" width="160">
        <template #default="s">{{ s.row.taken_at || '-' }}</template>
      </el-table-column>
      <el-table-column label="发布时间" width="160">
        <template #default="s">{{ s.row.created_at?.slice(0, 16) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="s">
          <el-button size="small" @click="handleEdit(s.row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="handleDelete(s.row.id)">
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 发布/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑任务' : '发布新任务'" width="550px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="任务标题" prop="title">
          <el-input v-model="form.title" placeholder="如：前端开发任务" />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="描述任务内容和要求" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类" prop="category">
              <el-select v-model="form.category" style="width:100%">
                <el-option label="前端" value="前端" /><el-option label="后端" value="后端" />
                <el-option label="设计" value="设计" /><el-option label="DevOps" value="DevOps" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="难度">
              <el-select v-model="form.difficulty" style="width:100%">
                <el-option label="简单" value="简单" /><el-option label="中等" value="中等" /><el-option label="困难" value="困难" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="赏金" prop="price">
              <el-input-number v-model="form.price" :min="1" :step="50" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工期(天)">
              <el-input-number v-model="form.duration" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="技能要求">
          <el-select v-model="form.skills" multiple filterable allow-create default-first-option placeholder="输入技能后回车" style="width:100%" />
        </el-form-item>
        <el-form-item label="状态" v-if="editId">
          <el-select v-model="form.status" style="width:100%">
            <el-option label="草稿" :value="0" />
            <el-option label="进行中" :value="1" />
            <el-option label="已暂停" :value="2" />
            <el-option label="已完成" :value="3" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitForm">{{ editId ? '保存' : '发布' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from '../../utils/request'

const taskList = ref([])
const loading = ref(false)
const searchQuery = ref('')

const statusLabel = (s) => ({ 0: '草稿', 1: '进行中', 2: '已暂停', 3: '已完成' }[s] || s)
const statusTag = (s) => ({ 0: 'info', 1: 'success', 2: 'warning', 3: '' }[s] || 'info')

const dialogVisible = ref(false)
const submitLoading = ref(false)
const editId = ref(null)
const formRef = ref(null)
const form = reactive({ title: '', description: '', category: '前端', difficulty: '中等', price: 100, duration: 7, skills: [], status: 1 })
const rules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  price: [{ required: true, message: '请设置赏金', trigger: 'blur' }],
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await axios.get('/mentor/tasks', {
      params: { keyword: searchQuery.value || undefined }
    })
    taskList.value = res.data || res
  } catch { ElMessage.error('获取任务列表失败') }
  finally { loading.value = false }
}

const resetForm = () => {
  Object.assign(form, { title: '', description: '', category: '前端', difficulty: '中等', price: 100, duration: 7, skills: [], status: 1 })
  editId.value = null
}

const handleCreate = () => { resetForm(); dialogVisible.value = true }

const handleEdit = (row) => {
  editId.value = row.id
  Object.assign(form, {
    title: row.title || '', description: row.description || '', category: row.category || '前端',
    difficulty: row.difficulty || '中等', price: row.price || 100, duration: row.duration || 7,
    skills: Array.isArray(row.skills) ? [...row.skills] : [], status: row.status ?? 1
  })
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      const payload = { ...form }
      if (editId.value) {
        await axios.put(`/mentor/tasks/${editId.value}`, payload)
        ElMessage.success('更新成功')
      } else {
        await axios.post('/mentor/tasks', payload)
        ElMessage.success('发布成功')
      }
      dialogVisible.value = false
      fetchTasks()
    } catch { ElMessage.error('操作失败') }
    finally { submitLoading.value = false }
  })
}

const handleDelete = async (id) => {
  try {
    await axios.delete(`/mentor/tasks/${id}`)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch { ElMessage.error('删除失败') }
}

onMounted(() => fetchTasks())
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }
</style>
