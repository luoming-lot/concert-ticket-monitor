import { defineStore } from 'pinia'
import { authAPI } from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: null,
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo?.username || '管理员',
  },

  actions: {
    async login(username, password) {
      const res = await authAPI.login({ username, password })
      this.token = res.access_token
      localStorage.setItem('token', res.access_token)
      await this.fetchUserInfo()
    },

    async fetchUserInfo() {
      try {
        const res = await authAPI.getInfo()
        this.userInfo = res
      } catch {
        this.userInfo = { username: 'admin', role: 'admin' }
      }
    },

    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
    },
  },
})
