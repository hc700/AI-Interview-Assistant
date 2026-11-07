import axios from 'axios'
import { message } from 'ant-design-vue'

const api = axios.create({ baseURL: '/api', timeout: 30000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
    }
    return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)))
  }
)

// 统一的消息提示
export function toastError(e) {
  message.error(typeof e === 'string' ? e : e.message || '操作失败')
}

export default api
