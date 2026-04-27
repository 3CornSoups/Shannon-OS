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
    }
  ]
})

export default router
