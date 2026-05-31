<template>
  <div class="dashboard-container">
    <!-- 1. 关键指标卡片区域 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-blue"><el-icon><Briefcase /></el-icon></div>
            <div class="text-box">
              <p class="label">发布任务总数</p>
              <p class="number">12</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-green"><el-icon><Clock /></el-icon></div>
            <div class="text-box">
              <p class="label">进行中</p>
              <p class="number">5</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-orange"><el-icon><Bell /></el-icon></div>
            <div class="text-box">
              <p class="label">待审核简历</p>
              <p class="number">8</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-purple"><el-icon><Check /></el-icon></div>
            <div class="text-box">
              <p class="label">已完成</p>
              <p class="number">24</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 2. 快捷入口与近期动态 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never" header="近期任务动态">
          <el-timeline>
            <el-timeline-item timestamp="2026-05-03" placement="top">
              <el-card>
                <h4>前端开发任务 - 状态变更为“进行中”</h4>
                <p>用户 张三 已接单</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item timestamp="2026-05-02" placement="top">
              <el-card>
                <h4>UI 设计任务 - 收到新投递</h4>
                <p>收到 1 份新的简历申请</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" header="快捷操作">
          <div class="quick-actions">
            <el-button type="primary" icon="Plus" class="w-100 mb-2">发布新任务</el-button>
            <el-button icon="Search" class="w-100 mb-2">查看人才库</el-button>
            <el-button icon="Wallet" class="w-100">充值/结算</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { Briefcase, Clock, Bell, Check, Plus, Search, Wallet } from '@element-plus/icons-vue'
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }
.mb-2 { margin-bottom: 10px; }
.w-100 { width: 100%; }

.stat-card {
  border-radius: 8px;
}
.card-content {
  display: flex;
  align-items: center;
}
.icon-box {
  width: 50px;
  height: 50px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  margin-right: 15px;
}
.bg-blue { background-color: #409EFF; }
.bg-green { background-color: #67C23A; }
.bg-orange { background-color: #E6A23C; }
.bg-purple { background-color: #909399; }

.number { font-size: 24px; font-weight: bold; color: #303133; margin: 0; }
.label { font-size: 14px; color: #606266; margin: 0; }
</style>