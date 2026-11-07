<template>
  <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#F4F7FF,#EBEFFF);">
    <a-card style="width:400px;border-radius:16px;box-shadow:0 10px 40px rgba(59,91,255,.12);" :bordered="false">
      <div class="logo" style="justify-content:center;margin-bottom:8px;">
        <span class="logo-mark"><svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" fill="#fff"/></svg></span>
        <span style="font-size:19px;">AI 模拟面试助手</span>
      </div>
      <p style="text-align:center;color:var(--t3);margin-bottom:24px;">登录后云端保存面试历史与成长曲线</p>

      <a-tabs v-model:active-key="tab" centered>
        <a-tab-pane key="login" tab="登录">
          <a-form layout="vertical" :model="loginForm" @finish="doLogin">
            <a-form-item label="邮箱" name="email" required>
              <a-input v-model:value="loginForm.email" placeholder="demo@interview.cn" size="large" />
            </a-form-item>
            <a-form-item label="密码" name="password" required>
              <a-input-password v-model:value="loginForm.password" placeholder="123456" size="large" />
            </a-form-item>
            <a-button type="primary" html-type="submit" size="large" block :loading="loading">登 录</a-button>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="register" tab="注册">
          <a-form layout="vertical" :model="regForm" @finish="doRegister">
            <a-form-item label="昵称" name="nickname">
              <a-input v-model:value="regForm.nickname" placeholder="怎么称呼你" size="large" />
            </a-form-item>
            <a-form-item label="邮箱" name="email" required>
              <a-input v-model:value="regForm.email" placeholder="you@example.com" size="large" />
            </a-form-item>
            <a-form-item label="密码（至少 6 位）" name="password" required>
              <a-input-password v-model:value="regForm.password" size="large" />
            </a-form-item>
            <a-button type="primary" html-type="submit" size="large" block :loading="loading">注 册</a-button>
          </a-form>
        </a-tab-pane>
      </a-tabs>

      <div class="note-strip" style="margin-top:8px;">
        演示账号：<b>demo@interview.cn</b> / <b>123456</b>（已含历史面试数据）；也可以不登录直接<a @click="$router.push('/config')" style="color:var(--primary);cursor:pointer;">免登录练习</a>。
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import api, { toastError } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const tab = ref('login')
const loading = ref(false)

const loginForm = reactive({ email: 'demo@interview.cn', password: '123456' })
const regForm = reactive({ email: '', password: '', nickname: '' })

async function doLogin() {
  loading.value = true
  try {
    const res = await api.post('/auth/login', loginForm)
    userStore.setAuth(res.token, res.user)
    message.success(`欢迎回来，${res.user.nickname}`)
    router.push('/profile')
  } catch (e) { toastError(e) } finally { loading.value = false }
}

async function doRegister() {
  loading.value = true
  try {
    const res = await api.post('/auth/register', regForm)
    userStore.setAuth(res.token, res.user)
    message.success('注册成功，已自动登录')
    router.push('/profile')
  } catch (e) { toastError(e) } finally { loading.value = false }
}
</script>
