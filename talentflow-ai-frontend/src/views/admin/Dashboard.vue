<template>
  <div class="dashboard">
    <!-- 1. 关键指标卡 -->
    <div class="cards-row">
      <div class="stat-card">
        <div class="stat-label">用户总数</div>
        <div class="stat-value">{{ overview.total_users ?? '-' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">职位总数</div>
        <div class="stat-value">{{ overview.total_jobs ?? '-' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">简历总数</div>
        <div class="stat-value">{{ overview.total_resumes ?? '-' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">待审核简历</div>
        <div class="stat-value warning">{{ overview.pending_reviews ?? '-' }}</div>
      </div>
    </div>

    <!-- 2. 图表区 -->
    <div class="charts-row">
      <div class="chart-panel">
        <h3 class="chart-title">近七天简历入库趋势</h3>
        <div ref="trendChart" class="chart-box"></div>
      </div>
      <div class="chart-panel">
        <h3 class="chart-title">技能分类占比</h3>
        <div ref="pieChart" class="chart-box"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import axios from '../../utils/request'

const overview = reactive({
  total_users: null,
  total_jobs: null,
  total_resumes: null,
  pending_reviews: null,
})

const trendChart = ref(null)
const pieChart = ref(null)
let trendInstance = null
let pieInstance = null

// 提取工具函数
const weekDays = () => {
  const days = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    days.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return days
}

const mapTrend = (raw) => {
  const days = weekDays()
  const map = {}
  raw.forEach(r => { map[r.date] = r.count })
  return days.map(d => {
    const iso = toIsoDate(d)
    return map[iso] ?? map[d] ?? 0
  })
}

const toIsoDate = (label) => {
  const [m, d] = label.split('/')
  const now = new Date()
  const year = now.getFullYear()
  const month = String(Number(m)).padStart(2, '0')
  const day = String(Number(d)).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 折线图配置
const trendOption = (dates, counts) => ({
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
  xAxis: { type: 'category', data: dates, boundaryGap: false },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{
    type: 'line',
    data: counts,
    smooth: true,
    lineStyle: { color: '#409EFF', width: 2 },
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(64,158,255,0.3)' },
        { offset: 1, color: 'rgba(64,158,255,0.02)' },
      ]),
    },
    itemStyle: { color: '#409EFF' },
  }],
})

// 环形饼图配置
const pieOption = (data) => {
  const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#B37FEB', '#36CFC9']
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: { fontSize: 12 },
    },
    color: colors,
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
      },
      data: data.filter(d => d.value > 0),
    }],
  }
}

// 渲染
const renderCharts = (trendData, distData) => {
  nextTick(() => {
    if (trendChart.value) {
      if (!trendInstance) trendInstance = echarts.init(trendChart.value)
      const days = weekDays()
      trendInstance.setOption(trendOption(days, mapTrend(trendData)))
    }
    if (pieChart.value) {
      if (!pieInstance) pieInstance = echarts.init(pieChart.value)
      pieInstance.setOption(pieOption(distData))
    }
  })
}

// 防抖 resize
let resizeTimer = null
const handleResize = () => {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    trendInstance?.resize()
    pieInstance?.resize()
  }, 200)
}

const fetchStats = async () => {
  try {
    const res = await axios.get('/admin/stats/overview')
    const d = res.data || res
    Object.assign(overview, d.overview || {})
    renderCharts(d.trend || [], d.distribution || [])
  } catch {
    console.error('获取统计数据失败')
  }
}

onMounted(() => {
  fetchStats()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendInstance?.dispose()
  pieInstance?.dispose()
})
</script>

<style scoped>
.dashboard { padding: 20px; background: #f5f7fa; min-height: 100vh; }

/* 指标卡 */
.cards-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }
.stat-card {
  background: #fff; border-radius: 8px; padding: 24px 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align: center;
}
.stat-label { font-size: 14px; color: #909399; margin-bottom: 8px; }
.stat-value { font-size: 32px; font-weight: 700; color: #303133; }
.stat-value.warning { color: #E6A23C; }

/* 图表 */
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.chart-panel { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.chart-title { font-size: 15px; font-weight: 600; color: #303133; margin: 0 0 12px 0; border-left: 4px solid #409EFF; padding-left: 10px; }
.chart-box { width: 100%; height: 360px; }

@media (max-width: 1200px) {
  .cards-row { grid-template-columns: repeat(2, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
}
</style>
