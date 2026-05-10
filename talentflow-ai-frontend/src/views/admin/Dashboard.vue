<template>
  <div class="admin-dashboard">
    <h2>基础数据统计</h2>
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="card-content">
            <div class="title">注册用户</div>
            <div class="number">12,345</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="card-content">
            <div class="title">实战项目数</div>
            <div class="number">86</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="card-content">
            <div class="title">今日投递</div>
            <div class="number">342</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="card-content">
            <div class="title">待审核任务</div>
            <div class="number warning">12</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 这里可以放 ECharts 图表容器 -->
    <div style="height: 400px; margin-top: 30px; border: 1px dashed #ccc; display: flex; align-items: center; justify-content: center; color: #999;">
      [ 数据趋势图表区域 ]
    </div>
  </div>
</template>

<style scoped>
.card-content {
  text-align: center;
}
.title { color: #999; font-size: 14px; }
.number { font-size: 28px; font-weight: bold; margin-top: 10px; }
.warning { color: #E6A23C; }
</style>