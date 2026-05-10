<template>
  <div class="cockpit-page">
    <h2>求职驾驶舱</h2>

    <!-- A. 顶部：简历状态与通知 -->
    <el-row :gutter="20" class="top-section">
      <el-col :span="16">
        <el-card class="resume-card">
          <div class="flex justify-between items-center">
            <div>
              <h3>个人简历完善度</h3>
              <p class="text-sm text-gray-500">完善简历可提高 AI 推荐匹配度</p>
            </div>
            <div class="w-1/2">
              <el-progress :percentage="80" status="success" />
            </div>
            <el-button type="primary" plain @click="handleEditResume">
              <el-icon><Edit /></el-icon> 编辑简历
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="notification-card">
           <div class="flex justify-between items-center">
              <span>消息通知</span>
              <el-badge :value="3" type="danger" :max="9">
                <el-icon size="20"><Bell /></el-icon>
              </el-badge>
           </div>
           <!-- 模拟消息列表 -->
           <div class="mt-4 space-y-2">
              <div class="text-sm">🎉 恭喜！你的任务《官网重构》已通过验收</div>
              <div class="text-sm">📩 字节跳动 发起了面试邀请</div>
           </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-4">
      <!-- B. 左侧：能力雷达图 -->
      <el-col :span="8">
        <el-card header="能力雷达图 (基于实战数据)">
          <div id="radar-chart" style="height: 300px;">
            <!-- ECharts 组件挂载点 -->
            <div class="mock-chart">[ 雷达图组件 ]</div>
          </div>
          <div class="mt-2 text-xs text-center text-gray-400">
            * 数据来源于已完成的实战任务
          </div>
        </el-card>
      </el-col>

      <!-- B. 右侧：AI 推荐 -->
      <el-col :span="16">
        <el-card header="AI 智能职位推荐">
          <el-table :data="jobList" style="width: 100%">
            <el-table-column prop="title" label="职位" />
            <el-table-column prop="company" label="公司" />
            <el-table-column prop="salary" label="薪资" />
            <el-table-column prop="match" label="匹配度">
              <template #default="scope">
                <el-tag :type="scope.row.match > 80 ? 'success' : 'warning'">
                  {{ scope.row.match }}% 匹配
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作">
              <template #default>
                <el-button type="primary" link @click="handleApply">一键投递</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- C. 底部：投递记录 (新增) -->
    <el-card header="我的投递记录" class="mt-4">
      <el-table :data="appliedList" style="width: 100%">
        <el-table-column prop="title" label="职位" />
        <el-table-column prop="company" label="公司" />
        <el-table-column prop="status" label="状态">
           <template #default="scope">
              <el-tag :type="getStatusTag(scope.row.status)">
                {{ scope.row.status }}
              </el-tag>
           </template>
        </el-table-column>
        <el-table-column prop="date" label="投递时间" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { Edit, Bell } from '@element-plus/icons-vue'

// 模拟数据
const jobList = [
  { title: '高级前端工程师', company: '字节跳动', salary: '25k-40k', match: 92 },
  { title: '全栈开发工程师', company: '阿里巴巴', salary: '30k-50k', match: 75 },
]

const appliedList = [
  { title: 'Vue 前端开发', company: '某初创公司', status: '已投递', date: '2024-05-01' },
  { title: 'Web3 交互开发', company: '独角兽企业', status: '面试中', date: '2024-04-28' },
]

const handleEditResume = () => { /* 跳转简历编辑 */ }
const handleApply = () => { /* 投递逻辑 */ }
const getStatusTag = (status) => {
    if(status === '面试中') return 'warning'
    if(status === '已投递') return 'info'
    return 'success'
}
</script>

<style scoped>
.cockpit-page { padding: 10px; }
.mock-chart { display: flex; align-items: center; justify-content: center; height: 100%; color: #999; background: #f9f9f9; border: 1px dashed #ddd; }
</style>