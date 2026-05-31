import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'

// --- 布局组件 ---
import MainLayout from '../layout/MainLayout.vue'
import AdminLayout from '../layout/AdminLayout.vue'
import HRLayout from '../layout/HRLayout.vue'

// --- 页面组件 ---
// 1. 用户端
import LoginView from '../views/LoginView.vue'
import Square from '../views/Square.vue'
import Charging from '../views/Charging.vue'
import Startup from '../views/Startup.vue'
import Referral from '../views/Referral.vue'
import Insights from '../views/Insights.vue'

// Phase 1: Dashboard 子模块
import DashboardLayout from '../views/user/dashboard/DashboardLayout.vue'
import TaskBoard from '../views/user/dashboard/TaskBoard.vue'
import JobCockpit from '../views/user/dashboard/JobCockpit.vue'
import TaskDetail from '../views/user/dashboard/TaskDetail.vue'
import ResumeManager from '../views/user/dashboard/ResumeManager.vue'

// 2. 管理端
import AdminDashboard from '../views/admin/Dashboard.vue'
import AdminUsers from '../views/admin/Users.vue'
import AdminProjects from '../views/admin/Projects.vue'
import AdminJobs from '../views/admin/Jobs.vue'
import AdminResumes from '../views/admin/Resumes.vue'


// 3.hr管理端
import HrDashboard from '../views/hr/Dashboard.vue'
import HrApplications from '../views/hr/Applications.vue'
import HrFinance from '../views/hr/Finance.vue'
import HrTask from '../views/hr/Task.vue'

// ==========================================
// 1. 类型声明扩展 (JS 写法)
// ==========================================
// 在 JS 中，我们通过 JSDoc 或者简单的忽略检查来告诉编辑器 meta 有哪些属性
/**
 * @typedef {Object} RouteMeta
 * @property {boolean} [isPublic] - 是否公开页面
 * @property {boolean} [requiresAuth] - 是否需要登录
 * @property {string} [role] - 需要的角色
 */

const routes = [
  // --- 公共路由 ---
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { isPublic: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { isPublic: true }
  },

  // --- 用户端路由 ---
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: '/dashboard/tasks' },

      // 蒲公英成长中心
      {
        path: 'dashboard',
        component: DashboardLayout,
        meta: { requiresAuth: true }, // 父级标记需要登录
        children: [
          { path: 'tasks', name: 'TaskBoard', component: TaskBoard },
          { path: 'jobs', name: 'JobCockpit', component: JobCockpit },
          { path: 'tasks/:id', name: 'TaskDetail', component: TaskDetail },
          { path: 'resume', name: 'resumes', component: ResumeManager },
          { path: 'applications', name: 'MyApps', component: () => import('../views/user/dashboard/Applications.vue') },
        ]
      },
      // 其他用户页面 (如果不加 meta，默认为公开)
      { path: 'square', name: 'Square', component: Square },
      { path: 'charging', name: 'Charging', component: Charging },
      { path: 'startup', name: 'Startup', component: Startup },
      { path: 'referral', name: 'Referral', component: Referral },
      { path: 'insights', name: 'Insights', component: Insights },
    ]
  },

  // --- 管理后台路由 ---
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true, role: 'admin' }, // 标记需要管理员权限
    children: [
      { path: 'dashboard', component: AdminDashboard },
      { path: 'users', component: AdminUsers },
      
      // 用户详情页路由
      {
        path: 'users/:id',           // 1. 动态路径参数 :id
        name: 'UserDetail',     // 2. 命名路由，方便跳转
        component: () => import('../views/admin/user_detail.vue'), // 3. 懒加载详情页组件
        props: true,                 // 4. 关键配置：将 params 中的 id 作为 props 传给组件
        meta: { requiresAuth: true, role: 'admin' } // 5. 继承父级的权限控制
      },
      
      { path: 'projects', component: AdminProjects },
      { path: 'jobs', component: AdminJobs },
      { path: 'resumes', component: AdminResumes }
    ]
  },


  // 2. 新增：HR 路由
  {
    path: '/hr',
    component: HRLayout,
    meta: { requiresAuth: true, role: 'hr' }, // 标记需要 hr 角色
    redirect: '/hr/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/hr/Dashboard.vue'), meta: { title: '工作台' } },
      { path: 'tasks', component: () => import('../views/hr/Task.vue'), meta: { title: '任务管理' } },
      { path: 'applications', component: () => import('../views/hr/Applications.vue'), meta: { title: '投递管理' } },
      { path: 'finance', component: () => import('../views/hr/Finance.vue'), meta: { title: '财务结算' } }
    ]
  },

  // --- 404 重定向 ---
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard/tasks'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ==========================================
// 2. 全局前置守卫
// ==========================================
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const token = userStore.token
  const userRole = userStore.role // 假设后端返回 '1':管理员, '2':普通用户, '3':HR

  // 1. 公共页面 (登录页等)
  if (to.meta.isPublic) {
    if (token) {
      // 已登录，根据角色分流
      if (userRole === '1'  || userRole === '1' || userRole === 'admin') {
        next('/admin/dashboard')
      } else if (userRole === '2' || userRole === 2 || userRole === 'hr') { // 判断 HR
        next('/hr/dashboard')
      } else {
        next('/dashboard/tasks') // 普通用户
      }
    } else {
      next()
    }
    return
  }

  // 2. 需要登录的页面
  if (to.meta.requiresAuth) {
    if (!token) {
      next('/login')
    } else if (to.meta.role === 'admin') {
      // 管理员专属区域拦截
      if (userRole === '1' || userRole === 1  || userRole === 'admin') {
        next()
      } else {
        next('/dashboard/tasks') // 非管理员强制踢出
      }
    } else if (to.path.startsWith('/hr')) {
      // HR 专属区域拦截 (可选，增加安全性)
      if (userRole === '2' || userRole ===  2 || userRole === 'hr') {
        next()
      } else {
        next('/dashboard/tasks')
      }
    } else {
      next() // 其他已登录用户页面
    }
  } else {
    next()
  }
})

// router.beforeEach((to, from, next) => {
//   const userStore = useUserStore()
//   const token = userStore.token
//   const userRole = userStore.role // 获取角色，可能是 '0', '1', '2' 或 'admin'

//   // 1. 如果是公共页面 (如登录页)
//   if (to.meta.isPublic) {
//     if (token) {
//       // 已登录：根据角色重定向，避免重复登录
//       // 兼容判断：如果是 '1' (后端定义) 或者 'admin' (前端定义) 都算管理员
//       if (userRole === '1' || userRole === 1 || userRole === 'admin') {
//         next('/admin/dashboard')
//       } else {
//         next('/dashboard/tasks')
//       }
//     } else {
//       next() // 未登录，允许访问登录页
//     }
//     return
//   }

//   // 2. 如果目标路由需要登录 (requiresAuth: true)
//   if (to.meta.requiresAuth) {
//     if (!token) {
//       // 未登录：强制跳转登录页
//       next('/login')
//     } else if (to.meta.role === 'admin') {
//       // 需要管理员权限：检查角色
//       if (userRole === '1' || userRole === 1 || userRole === 'admin') {
//         next() // 是管理员，通过
//       } else {
//         // 不是管理员，重定向到用户首页
//         next('/dashboard/tasks')
//       }
//     } else {
//       next() // 需要登录，且不是管理员专属页面，直接通过
//     }
//   } else {
//     // 3. 不需要登录的页面 (如 /square)，直接通过
//     next()
//   }
// })

export default router