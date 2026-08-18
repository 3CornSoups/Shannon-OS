import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('../pages/Dashboard.vue')
    },
    {
      path: '/servers',
      name: 'Servers',
      component: () => import('../pages/Servers.vue')
    },
    {
      path: '/history',
      name: 'History',
      component: () => import('../pages/History.vue')
    },
    {
      path: '/monitoring',
      name: 'Monitoring',
      component: () => import('../pages/Monitoring.vue')
    },
    {
      path: '/templates',
      name: 'Templates',
      component: () => import('../pages/Templates.vue')
    },
    {
      path: '/showcase',
      name: 'Showcase',
      component: () => import('../pages/Showcase.vue')
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('../pages/Settings.vue')
    },
    {
      path: '/monitor-overview',
      name: 'MonitorOverview',
      component: () => import('../pages/MonitorDashboard.vue')
    },
    {
      path: '/alerts',
      name: 'Alerts',
      component: () => import('../pages/Alerts.vue')
    },
    {
      path: '/alerts/rules',
      name: 'AlertRules',
      component: () => import('../pages/AlertRules.vue')
    },
    {
      path: '/tools',
      name: 'Tools',
      component: () => import('../pages/Tools.vue')
    },
    {
      path: '/echo',
      name: 'Echo',
      component: () => import('../pages/Echo.vue')
    },
    {
      path: '/echo/reports',
      name: 'EchoReports',
      component: () => import('../pages/EchoReports.vue')
    },
    {
      path: '/memory',
      name: 'Memory',
      component: () => import('../pages/Memory.vue')
    }
  ]
})

export default router
