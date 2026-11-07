import { defineStore } from 'pinia'
import api from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    quota: null,
  }),
  getters: {
    isLogin: (s) => !!s.token,
    isMember: (s) => !!s.user?.is_member,
  },
  actions: {
    setAuth(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify(user))
    },
    async refresh() {
      if (!this.token) return
      try {
        this.user = await api.get('/auth/me')
        localStorage.setItem('user', JSON.stringify(this.user))
        const q = await api.get('/users/me/quota')
        this.quota = q
      } catch {
        this.logout(false)
      }
    },
    async loadQuota() {
      if (!this.token) return
      this.quota = await api.get('/users/me/quota')
    },
    logout(showTip = true) {
      this.token = ''
      this.user = null
      this.quota = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (showTip) window.$message?.success('已退出登录')
    },
  },
})
