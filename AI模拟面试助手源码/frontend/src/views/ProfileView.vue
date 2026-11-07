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

    <!-- 未登录 -->
    <div v-if="!userStore.isLogin" style="max-width:760px;margin:60px auto;padding:0 24px;">
      <a-card style="border-radius:14px;text-align:center;" :bordered="false">
        <h3>登录后查看云端面试数据</h3>
        <p style="color:var(--t2);">登录可云端保存简历、面试历史与成长曲线；<br />游客模式的本地记录：</p>
        <div v-if="guestHistory.length" style="text-align:left;">
          <div v-for="(h, i) in guestHistory" :key="i"
               style="display:flex;justify-content:space-between;padding:10px 4px;border-bottom:1px dashed var(--line2);font-size:14px;">
            <span>{{ h.date }} · {{ h.position }}</span>
            <b :style="{ color: h.score >= 75 ? 'var(--green)' : 'var(--orange)' }">{{ h.score }} 分</b>
          </div>
        </div>
        <p v-else style="color:var(--t3);">暂无本地记录，去<a @click="$router.push('/config')" style="color:var(--primary);cursor:pointer;">练一场</a>吧</p>
        <a-button type="primary" size="large" style="margin-top:12px;" @click="$router.push('/login')">登录 / 注册</a-button>
      </a-card>
    </div>

    <!-- 已登录 -->
    <div v-else style="max-width:1080px;margin:28px auto;padding:0 24px;display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap;">
      <!-- 侧栏 -->
      <a-card style="width:240px;flex:none;border-radius:14px;" :bordered="false" body-style="padding:14px;">
        <div style="display:flex;align-items:center;gap:10px;padding:8px 6px 14px;">
          <a-avatar :size="44" style="background:#3B5BFF;font-size:18px;">{{ userStore.user?.nickname?.[0] || '友' }}</a-avatar>
          <div>
            <div style="font-weight:700;">{{ userStore.user?.nickname }}<span v-if="userStore.isMember" class="pro-badge">PRO</span></div>
            <p style="color:var(--t3);font-size:12px;margin:4px 0 0;">{{ userStore.user?.email }}</p>
          </div>
        </div>
        <div v-for="m in menus" :key="m.key"
             :style="{ padding:'10px 12px', borderRadius:8, cursor:'pointer', fontSize:14,
                       background: menu === m.key ? 'var(--primary-bg)' : 'transparent',
                       color: menu === m.key ? 'var(--primary)' : 'var(--t2)', fontWeight: menu === m.key ? 600 : 400 }"
             @click="menu = m.key">{{ m.icon }} {{ m.label }}</div>
        <div style="border-top:1px solid var(--line2);margin-top:8px;padding-top:8px;">
          <div style="padding:10px 12px;color:var(--red);cursor:pointer;font-size:14px;" @click="logout">退出登录</div>
        </div>
      </a-card>

      <!-- 主区 -->
      <div style="flex:1;min-width:380px;">
        <!-- 总览 -->
        <template v-if="menu === 'overview'">
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:20px;">
            <a-card :bordered="false" style="border-radius:14px;text-align:center;">
              <div style="font-size:30px;font-weight:800;color:var(--primary);">{{ overview.total_sessions || 0 }}</div>
              <p style="color:var(--t3);margin:6px 0 0;">累计面试场次</p>
            </a-card>
            <a-card :bordered="false" style="border-radius:14px;text-align:center;">
              <div style="font-size:30px;font-weight:800;color:var(--green);">{{ overview.avg_score || 0 }}</div>
              <p style="color:var(--t3);margin:6px 0 0;">平均综合得分</p>
            </a-card>
            <a-card :bordered="false" style="border-radius:14px;text-align:center;">
              <div style="font-size:30px;font-weight:800;color:var(--primary);">{{ overview.quota?.used ?? '-' }} / {{ overview.quota?.limit ?? '-' }}</div>
              <p style="color:var(--t3);margin:6px 0 0;">本月免费额度 · <a @click="$router.push('/pricing')" style="color:var(--orange);cursor:pointer;">升级不限次</a></p>
            </a-card>
          </div>

          <a-card :bordered="false" style="border-radius:14px;margin-bottom:20px;">
            <h3 style="margin-top:0;">成长曲线（近 {{ trend.length }} 场）</h3>
            <div v-if="trend.length >= 2" style="height:200px;">
              <svg viewBox="0 0 700 200" preserveAspectRatio="none" style="width:100%;height:100%;">
                <line v-for="y in [50, 100, 150]" :key="y" x1="40" :y1="y" x2="690" :y2="y" stroke="#F0F1F5" />
                <polyline :points="trendPoints" fill="none" stroke="#3B5BFF" stroke-width="2.5"
                          stroke-linejoin="round" stroke-linecap="round" />
                <circle v-for="(p, i) in trendDots" :key="i" :cx="p.x" :cy="p.y" r="4" fill="#3B5BFF" />
                <text v-for="(t, i) in trend" :key="'t' + i" :x="trendDots[i]?.x" :y="trendDots[i]?.y - 10"
                      font-size="11" fill="#4E5969" text-anchor="middle">{{ t.score }}</text>
              </svg>
            </div>
            <p v-else style="color:var(--t3);">完成至少 2 场面试后展示成长曲线，<a @click="$router.push('/config')" style="color:var(--primary);cursor:pointer;">去练一场 →</a></p>
          </a-card>

          <a-card :bordered="false" style="border-radius:14px;">
            <h3 style="margin-top:0;">面试历史</h3>
            <a-table :columns="histCols" :data-source="history" :pagination="false" size="small" row-key="id">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'score'">
                  <b :style="{ color: (record.score || 0) >= 75 ? 'var(--green)' : 'var(--orange)' }">{{ record.score ?? '-' }}</b>
                </template>
                <template v-else-if="column.key === 'op'">
                  <a v-if="record.status === 'completed' && record.score" @click="viewReport(record)"
                     style="color:var(--primary);cursor:pointer;">查看报告</a>
                  <a v-if="record.status === 'completed' && record.score" @click="downloadReportPdf(record)"
                     style="color:var(--primary);cursor:pointer;margin-left:10px;">下载 PDF</a>
                  <span v-if="!(record.status === 'completed' && record.score)" style="color:var(--t3);">未完成</span>
                </template>
              </template>
            </a-table>
          </a-card>
        </template>

        <!-- 我的简历 -->
        <template v-else-if="menu === 'cv'">
          <a-card :bordered="false" style="border-radius:14px;">
            <h3 style="margin-top:0;">已上传简历</h3>
            <div v-if="!resumes.length" style="color:var(--t3);padding:10px 0;">暂无简历</div>
            <div v-for="r in resumes" :key="r.id"
                 style="display:flex;align-items:center;gap:14px;padding:14px;border:1px solid var(--line2);border-radius:10px;margin-bottom:12px;">
              <span style="font-size:26px;">📄</span>
              <div style="flex:1;">
                <b>{{ r.file_name }}</b>
                <p style="color:var(--t3);font-size:12px;margin:4px 0 0;">
                  上传于 {{ r.uploaded_at }} · 提取技能：{{ (r.tech_tags || []).join(' / ') || '-' }}
                </p>
              </div>
              <a-popconfirm title="删除后不可恢复，确认？" @confirm="delResume(r)">
                <a-button danger size="small">删除</a-button>
              </a-popconfirm>
            </div>
            <a-upload :show-upload-list="false" :custom-request="uploadResume" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md">
              <a-button>＋ 上传新简历（PDF/Word/PPT/TXT ≤ 10MB）</a-button>
            </a-upload>
            <div class="note-strip" style="margin-top:14px;">🔐 隐私说明：简历仅用于生成定制面试问题；删除简历后系统立即清除全部相关数据。</div>
          </a-card>
        </template>

        <!-- 面试历史 -->
        <template v-else-if="menu === 'history'">
          <a-card :bordered="false" style="border-radius:14px;">
            <h3 style="margin-top:0;">全部面试历史</h3>
            <a-table :columns="histCols" :data-source="history" :pagination="false" size="small" row-key="id">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'score'">
                  <b :style="{ color: (record.score || 0) >= 75 ? 'var(--green)' : 'var(--orange)' }">{{ record.score ?? '-' }}</b>
                </template>
                <template v-else-if="column.key === 'op'">
                  <a v-if="record.status === 'completed' && record.score" @click="viewReport(record)"
                     style="color:var(--primary);cursor:pointer;">查看报告</a>
                  <a v-if="record.status === 'completed' && record.score" @click="downloadReportPdf(record)"
                     style="color:var(--primary);cursor:pointer;margin-left:10px;">下载 PDF</a>
                  <span v-if="!(record.status === 'completed' && record.score)" style="color:var(--t3);">未完成</span>
                </template>
              </template>
            </a-table>
          </a-card>
        </template>

        <!-- 会员与订阅 -->
        <template v-else-if="menu === 'member'">
          <a-card :bordered="false" style="border-radius:14px;text-align:center;">
            <template v-if="!sub.is_member">
              <h3 style="margin-top:0;">当前为免费版</h3>
              <p style="color:var(--t2);">
                每月 {{ overview.quota?.limit || 3 }} 场免费额度（本月已用
                <b>{{ overview.quota?.used ?? 0 }}</b>/{' ' }{{ overview.quota?.limit || 3 }}）。
                开通会员即可解锁不限次面试与完整深度报告。
              </p>
              <button class="btn-unlock" style="margin-top:8px;" @click="$router.push('/pricing')">升级会员 ¥39 起/月</button>
            </template>
            <template v-else>
              <h3 style="margin-top:0;">当前订阅 · {{ sub.plan_name }} <span class="pro-badge">PRO</span></h3>
              <div style="display:flex;flex-direction:column;gap:10px;max-width:420px;margin:0 auto;text-align:left;">
                <div style="display:flex;justify-content:space-between;"><span style="color:var(--t3);">到期时间</span><b>{{ sub.end_time }}</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:var(--t3);">续费方式</span><b>{{ sub.auto_renew ? '自动续费' : '不自动续费' }}</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:var(--t3);">权益</span><b>不限次面试 · 五维报告 · 简历定制</b></div>
              </div>
              <div style="margin-top:20px;">
                <a-popconfirm title="取消后当期权益保留至到期日，确认？" @confirm="cancelSub">
                  <a-button danger>取消订阅</a-button>
                </a-popconfirm>
              </div>
            </template>
          </a-card>
        </template>

        <!-- 账号设置 -->
        <template v-else>
          <a-card :bordered="false" style="border-radius:14px;">
            <h3 style="margin-top:0;">账号设置</h3>
            <div style="display:flex;flex-direction:column;gap:14px;max-width:520px;">
              <div style="display:flex;justify-content:space-between;"><span style="color:var(--t3);">手机号</span><b>{{ userStore.user?.phone || '未绑定' }}</b></div>
              <div style="display:flex;justify-content:space-between;"><span style="color:var(--t3);">邮箱</span><b>{{ userStore.user?.email }}</b></div>
              <div style="display:flex;justify-content:space-between;"><span style="color:var(--t3);">注册来源</span><b>邮箱注册</b></div>
              <div style="display:flex;justify-content:space-between;"><span style="color:var(--t3);">隐私设置</span><b style="color:var(--t3);font-weight:400;">默认拒绝将面试数据用于模型训练</b></div>
            </div>
          </a-card>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import api, { toastError } from '../api'
import { useUserStore } from '../stores/user'
import { useInterviewStore } from '../stores/interview'

const router = useRouter()
const userStore = useUserStore()
const store = useInterviewStore()

const menus = [
  { key: 'overview', icon: '📊', label: '总览' },
  { key: 'cv', icon: '📄', label: '我的简历' },
  { key: 'history', icon: '🕘', label: '面试历史' },
  { key: 'member', icon: '💎', label: '会员与订阅' },
  { key: 'account', icon: '⚙️', label: '账号设置' },
]
const menu = ref('overview')
const overview = ref({})
const history = ref([])
const resumes = ref([])
const sub = ref({ is_member: false })
const guestHistory = ref([])

const histCols = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
  { title: '岗位 / 难度', key: 'job', ellipsis: true },
  { title: '得分', dataIndex: 'score', key: 'score', width: 80 },
  { title: '操作', key: 'op', width: 150 },
]

const trend = computed(() => (overview.value.trend || []).slice(-12))
const trendDots = computed(() => {
  const arr = trend.value
  if (!arr.length) return []
  const stepX = arr.length > 1 ? 640 / (arr.length - 1) : 0
  return arr.map((t, i) => ({
    x: 40 + i * stepX,
    y: 170 - ((t.score - 50) / 50) * 140,
  }))
})
const trendPoints = computed(() => trendDots.value.map((p) => `${p.x},${p.y}`).join(' '))

async function loadAll() {
  if (!userStore.isLogin) {
    guestHistory.value = JSON.parse(localStorage.getItem('guestHistory') || '[]')
    return
  }
  try {
    overview.value = await api.get('/users/me/overview')
    history.value = (await api.get('/sessions')).map((s) => ({
      ...s,
      job: `${s.position_name} · ${['初级', '中级', '高级'][s.difficulty - 1] || '-'}`,
    }))
    resumes.value = await api.get('/users/me/resumes')
    sub.value = await api.get('/users/me/subscription')
  } catch (e) { toastError(e) }
}

async function viewReport(record) {
  try {
    await store.loadServerReport(record.id)
    router.push('/report')
  } catch (e) { toastError(e) }
}

/** 下载某场历史面试的 PDF 报告：新标签页加载报告并自动导出 */
function downloadReportPdf(record) {
  const { href } = router.resolve({ path: '/report', query: { session: record.id, download: '1' } })
  window.open(href, '_blank')
  message.info('已在新标签页生成 PDF 报告')
}

async function uploadResume({ file, onSuccess, onError }) {
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await api.post('/users/me/resumes', fd)
    resumes.value.unshift(res)
    message.success('简历上传并解析成功')
    onSuccess(res)
  } catch (e) { toastError(e); onError(e) }
}

async function delResume(r) {
  await api.delete(`/users/me/resumes/${r.id}`)
  resumes.value = resumes.value.filter((x) => x.id !== r.id)
  message.success('简历已删除')
}

async function cancelSub() {
  try {
    await api.post('/users/me/subscription/cancel')
    await userStore.refresh()
    sub.value = await api.get('/users/me/subscription')
    message.success('已取消订阅，权益保留至到期日')
  } catch (e) { toastError(e) }
}

function logout() {
  userStore.logout()
  message.success('已退出登录')
  router.push('/')
}

onMounted(async () => {
  if (userStore.isLogin) await userStore.refresh()
  await loadAll()
})
</script>
