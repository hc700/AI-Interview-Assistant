<template>
  <div>
    <header class="page-nav">
      <div class="nav-left">
        <div class="logo">
          <span class="logo-mark"><svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" fill="#fff"/></svg></span>
          <span>AI 模拟面试助手</span>
        </div>
        <nav class="nav-menu">
          <router-link class="nav-it" to="/">首页</router-link>
          <router-link class="nav-it" to="/config">开始面试</router-link>
          <router-link class="nav-it" to="/pricing">会员定价</router-link>
          <router-link class="nav-it" to="/profile">个人中心</router-link>
        </nav>
      </div>
      <div>
        <a-button v-if="!userStore.isLogin" type="primary" @click="$router.push('/login')">登录</a-button>
        <span v-else style="cursor:pointer;display:flex;align-items:center;" @click="$router.push('/profile')">
          <a-avatar style="background:#3B5BFF;">{{ userStore.user?.nickname?.[0] || '友' }}</a-avatar>
          <b style="margin:0 8px;">{{ userStore.user?.nickname }}</b>
          <span v-if="userStore.isMember" class="pro-badge">PRO</span>
        </span>
      </div>
    </header>

    <div style="max-width:1120px;margin:0 auto;padding:28px 24px;">
      <!-- 配额提示 -->
      <div class="note-strip" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <span v-if="userStore.isLogin">
          🎟️ 本月免费额度剩余
          <b v-if="quota" style="color:var(--orange);">{{ Math.max(quota.limit - quota.used, 0) }}/{{ quota.limit }}</b>
          场 <template v-if="quota && quota.used >= quota.limit && !quota.is_member">（已用完）</template>
          <span v-if="userStore.isMember">· 会员不限场次</span>
        </span>
        <span v-else>🕵️ 当前为游客模式：免登录即可完整体验一场面试，结果保存在本地浏览器</span>
        <a @click="$router.push('/pricing')" style="color:var(--orange);cursor:pointer;">开通会员，不限场次 →</a>
      </div>

      <div style="display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap;">
        <!-- 左侧配置表单 -->
        <a-card style="flex:1;min-width:400px;border-radius:14px;" :bordered="false">
          <h3 style="margin-top:0;">配置一场模拟面试</h3>

          <p class="f-label">① 目标岗位</p>
          <div style="display:flex;flex-wrap:wrap;gap:10px;">
            <a-button v-for="p in positions" :key="p.id" :type="form.positionId === p.id ? 'primary' : 'default'"
                      @click="form.positionId = p.id">{{ p.name }}</a-button>
          </div>

          <p class="f-label">② 难度级别</p>
          <div style="display:flex;gap:10px;">
            <a-button v-for="(d,i) in diffLabels" :key="i" :type="form.difficulty === i+1 ? 'primary' : 'default'"
                      @click="form.difficulty = i+1">{{ d }}</a-button>
          </div>

          <p class="f-label">③ 面试时长</p>
          <div style="display:flex;gap:10px;">
            <a-button v-for="m in [30,45,60]" :key="m" :type="form.durationMin === m ? 'primary' : 'default'"
                      @click="form.durationMin = m">{{ m }} 分钟</a-button>
          </div>

          <p class="f-label">④ 题目构成 <span style="color:#C0C6D1;font-weight:400;">· 拖动滑块自定义</span></p>
          <div v-for="m in mixItems" :key="m.key" style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">
            <span style="width:96px;font-size:14px;">{{ m.label }}</span>
            <a-slider v-model:value="form.questionMix[m.key]" :min="0" :max="m.max" style="flex:1;margin:0;" />
            <span style="width:40px;text-align:right;color:var(--t2);">{{ form.questionMix[m.key] }} 题</span>
          </div>

          <p class="f-label">⑤ 简历上传 <span style="color:#C0C6D1;font-weight:400;">可选 · 上传后 AI 将结合简历定制追问</span></p>
          <a-upload :show-upload-list="false" :custom-request="uploadResume" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md">
            <a-button :loading="uploading">{{ selectedResume ? '更换简历' : (userStore.isLogin ? '＋ 上传简历（PDF/Word/PPT/TXT ≤10MB）' : '＋ 游客上传简历（本场有效）') }}</a-button>
          </a-upload>
          <div v-if="selectedResume" style="margin-top:10px;line-height:1.6;">
            <a-tag color="green">已解析</a-tag>
            <b>{{ selectedResume.file_name }}</b>
            <div v-if="selectedResume.summary" style="color:var(--t3);font-size:12px;margin-top:4px;">
              摘要：{{ selectedResume.summary }}
            </div>
            <div v-if="(selectedResume.tech_tags || []).length" style="color:var(--t3);font-size:12px;margin-top:4px;">
              提取技能：{{ selectedResume.tech_tags.join(' / ') }}
            </div>
          </div>
          <div v-if="!userStore.isLogin" class="note-strip" style="margin-top:10px;">
            💡 登录后可云端保存简历，多设备同步并在个人中心管理
          </div>
        </a-card>

        <!-- 右侧面试说明书 -->
        <a-card style="width:340px;flex:none;border-radius:14px;background:linear-gradient(180deg,#F7F9FF,#fff);" :bordered="false">
          <h3 style="margin-top:0;">📋 面试说明书</h3>
          <div v-for="row in specRows" :key="row.k" style="display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px dashed var(--line2);font-size:14px;">
            <span style="color:var(--t3);">{{ row.k }}</span>
            <b>{{ row.v }}</b>
          </div>
          <a-button type="primary" size="large" block style="height:46px;margin-top:20px;" :loading="creating" @click="start">
            确认，开始面试
          </a-button>
          <p style="color:var(--t3);font-size:12px;text-align:center;margin:10px 0 0;">
            {{ userStore.isLogin ? '开始后消耗 1 次免费额度，中途取消不退还' : '游客模式不消耗额度，结果仅存本地' }}
          </p>
        </a-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import api, { toastError } from '../api'
import { useUserStore } from '../stores/user'
import { useInterviewStore } from '../stores/interview'

const router = useRouter()
const userStore = useUserStore()
const store = useInterviewStore()

const diffLabels = ['初级 0~2 年', '中级 2~5 年', '高级 5 年+']
const mixItems = [
  { key: 'voice', label: '🎤 语音问答', max: 8 },
  { key: 'coding', label: '💻 在线编程', max: 3 },
  { key: 'whiteboard', label: '📐 白板设计', max: 2 },
]

const positions = ref([])
const quota = ref(null)
const resumes = ref([])
const selectedResume = ref(null)
const uploading = ref(false)
const creating = ref(false)

const form = reactive({
  positionId: null,
  difficulty: 2,
  durationMin: 45,
  questionMix: { voice: 6, coding: 2, whiteboard: 1 },
  resumeId: null,
})

onMounted(async () => {
  positions.value = await api.get('/positions')
  if (positions.value.length) form.positionId = positions.value[0].id
  if (userStore.isLogin) {
    try {
      quota.value = await api.get('/users/me/quota')
      resumes.value = await api.get('/users/me/resumes')
      if (resumes.value.length) selectedResume.value = resumes.value[0]
    } catch { /* 忽略 */ }
  }
})

async function uploadResume({ file, onSuccess, onError }) {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    // 登录用户云端保存；游客仅解析本场使用
    const endpoint = userStore.isLogin ? '/users/me/resumes' : '/resume/parse'
    const res = await api.post(endpoint, fd)
    selectedResume.value = {
      id: res.id || null,
      file_name: res.file_name,
      summary: res.summary || '',
      tech_tags: res.tech_tags || [],
    }
    message.success('简历解析完成，将结合简历定制追问')
    onSuccess(res)
  } catch (e) {
    toastError(e)
    onError(e)
  } finally { uploading.value = false }
}

const specRows = computed(() => {
  const pos = positions.value.find((p) => p.id === form.positionId)
  const { voice, coding, whiteboard } = form.questionMix
  return [
    { k: '目标岗位', v: pos?.name || '-' },
    { k: '难度级别', v: diffLabels[form.difficulty - 1] },
    { k: '面试时长', v: `${form.durationMin} 分钟` },
    { k: '语音问答', v: `${voice} 题 · 约 ${Math.round(form.durationMin * 0.4)} 分钟` },
    { k: '在线编程', v: `${coding} 题 · 约 ${Math.round(form.durationMin * 0.4)} 分钟` },
    { k: '白板设计', v: `${whiteboard} 题 · 约 ${Math.max(form.durationMin * 0.2, 5)} 分钟` },
    { k: '简历定制', v: selectedResume.value ? '已开启' : '未上传' },
    { k: '预计用时', v: `约 ${Math.max(voice * 3 + coding * 9 + whiteboard * 8, 10)} 分钟` },
  ]
})

async function start() {
  if (!form.positionId) return message.warning('请选择目标岗位')
  if (form.questionMix.voice + form.questionMix.coding + form.questionMix.whiteboard === 0) {
    return message.warning('至少选择一道题目')
  }
  creating.value = true
  try {
    await store.createSession({ ...form, resume: selectedResume.value || null })
    message.success('面试已创建，AI 面试官正在进入房间…')
    router.push('/room/voice')
  } catch (e) {
    toastError(e)
  } finally { creating.value = false }
}
</script>

<style scoped>
.f-label { font-weight: 600; margin: 22px 0 12px; }
.f-label:first-of-type { margin-top: 12px; }
</style>
