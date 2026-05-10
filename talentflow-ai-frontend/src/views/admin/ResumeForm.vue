<!-- src/components/ResumeForm.vue -->
<template>
  <!-- 
    修改点：
    1. 使用 :model-value 和 @update:model-value 替代 v-model，更明确。
    2. 添加 top="5vh" 确保位置居中。
    3. 添加 append-to-body 防止被父级 overflow: hidden 遮挡。
  -->
  <el-dialog
    :model-value="props.modelValue"
    @update:model-value="(val) => emit('update:modelValue', val)"
    :title="isEdit ? '编辑简历' : '手动录入简历'"
    width="600px"
    top="5vh"
    append-to-body
    destroy-on-close
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="left"
    >
      <!-- 基础信息 -->
      <el-divider content-position="left">基础信息</el-divider>
      
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" placeholder="请输入求职者姓名" />
      </el-form-item>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="联系电话" prop="phone">
            <el-input v-model="form.phone" placeholder="请输入手机号" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="请输入邮箱" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 职位意向 -->
      <el-divider content-position="left">求职意向</el-divider>

      <el-form-item label="意向职位" prop="title">
        <el-input v-model="form.title" placeholder="例如：前端开发工程师" />
      </el-form-item>

      <el-form-item label="学历" prop="education">
        <el-select v-model="form.education" placeholder="请选择学历" style="width: 100%">
          <el-option label="大专" value="大专" />
          <el-option label="本科" value="本科" />
          <el-option label="硕士" value="硕士" />
          <el-option label="博士" value="博士" />
        </el-select>
      </el-form-item>

      <!-- 详细内容 -->
      <el-form-item label="个人简介" prop="summary">
        <el-input
          v-model="form.summary"
          type="textarea"
          :rows="3"
          placeholder="请简要描述个人优势或自我评价"
        />
      </el-form-item>

      <el-form-item label="项目经验" prop="project_experience">
        <el-input
          v-model="form.project_experience"
          type="textarea"
          :rows="3"
          placeholder="请描述主要项目经历"
        />
      </el-form-item>

      <!-- 技能标签 -->
      <el-form-item label="技能标签" prop="skills">
        <el-select
          v-model="form.skills"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入技能后回车添加"
          style="width: 100%"
        >
        </el-select>
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="form.status">
          <el-radio label="Pending">待审核</el-radio>
          <el-radio label="Active">已激活</el-radio>
        </el-radio-group>
      </el-form-item>

    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="submitForm">
          {{ isEdit ? '保存修改' : '立即录入' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watchEffect } from 'vue'; // 引入 watchEffect
import { ElMessage } from 'element-plus';
import axios from '../../utils/request';

const props = defineProps({
  modelValue: Boolean,
  editData: Object
});

const emit = defineEmits(['update:modelValue', 'success']);

const formRef = ref(null);
const loading = ref(false);

// 初始空表单
const initialForm = {
  name: '',
  phone: '',
  email: '',
  title: '',
  education: '',
  summary: '',
  project_experience: '',
  skills: [],
  status: 'Pending'
};

const form = reactive({ ...initialForm });

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入电话', trigger: 'blur' }],
  title: [{ required: true, message: '请输入意向职位', trigger: 'blur' }],
  education: [{ required: true, message: '请选择学历', trigger: 'change' }],
};

// 计算是否是编辑模式
const isEdit = computed(() => !!props.editData);

// 【重点修改】使用 watchEffect 监听弹窗显示
watchEffect(() => {
  if (props.modelValue) {
    console.log('弹窗已打开，当前模式:', isEdit.value ? '编辑' : '新增');
    
    if (isEdit.value && props.editData) {
      console.log('正在回填数据:', props.editData);
      
      // 逐个字段回填，确保字段名完全匹配
      Object.keys(form).forEach(key => {
        if (props.editData[key] !== undefined) {
          form[key] = props.editData[key];
        }
      });
    } else {
      // 重置为新增模式
      Object.assign(form, initialForm);
    }
  }
});

const submitForm = async () => {
  if (!formRef.value) return;
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        if (isEdit.value) {
          await axios.put(`/admin/resumes/${props.editData.id}`, form);
          ElMessage.success('更新成功');
        } else {
          await axios.post('/admin/resumes', form);
          ElMessage.success('录入成功');
        }
        
        emit('success');
        emit('update:modelValue', false);
        
      } catch (error) {
        ElMessage.error(isEdit.value ? '更新失败' : '录入失败');
        console.error(error);
      } finally {
        loading.value = false;
      }
    }
  });
};

const handleClose = () => {
  formRef.value?.resetFields();
};
</script>