import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
  { path: '/config', name: 'config', component: () => import('../views/ConfigView.vue') },
  { path: '/room/voice', name: 'voice', component: () => import('../views/VoiceView.vue') },
  { path: '/room/coding', name: 'coding', component: () => import('../views/CodingView.vue') },
  { path: '/room/whiteboard', name: 'whiteboard', component: () => import('../views/WhiteboardView.vue') },
  { path: '/report', name: 'report', component: () => import('../views/ReportView.vue') },
  { path: '/pricing', name: 'pricing', component: () => import('../views/PricingView.vue') },
  { path: '/profile', name: 'profile', component: () => import('../views/ProfileView.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

export default router
