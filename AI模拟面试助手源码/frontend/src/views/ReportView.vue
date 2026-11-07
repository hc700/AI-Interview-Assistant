<template>
  <div v-if="report">
    <RoomHeader :current="3" :finished="true" />

    <div ref="reportBody" class="report-body room-body" :class="{ capturing }">
      <div>
        <h2 style="margin:8px 0 6px;font-size:24px;">面试评分报告</h2>
        <p style="color:var(--t3);margin:0 0 20px;">
          {{ userStore.user?.nickname || '游客' }} · {{ report.session.position?.name || '-' }} ·
          {{ ['初级', '中级', '高级'][(report.session.difficulty || 2) - 1] }} ·
          {{ report.session.ended_at || new Date().toLocaleString('zh-CN') }}
        </p>
      </div>

      <!-- 顶部成绩卡 -->
      <a-card style="border-radius:14px;margin-bottom:20px;" :bordered="false">
        <div style="display:flex;gap:32px;align-items:center;flex-wrap:wrap;">
          <div class="ring-wrap">
            <svg width="160" height="160" viewBox="0 0 160 160">
              <circle cx="80" cy="80" r="66" fill="none" stroke="#EEF0F5" stroke-width="12" />
              <circle cx="80" cy="80" r="66" fill="none" stroke="#3B5BFF" stroke-width="12"
                      stroke-linecap="round" :stroke-dasharray="414.7"
                      :stroke-dashoffset="414.7 - 414.7 * (score / 100)"
                      transform="rotate(-90 80 80)" style="transition:stroke-dashoffset 1s ease;" />
            </svg>
            <div class="ring-num">{{ score }}<span class="ring-lab">综合得分 / 100</span></div>
          </div>
          <div style="flex:1;min-width:260px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
              <a-rate :value="score / 20" disabled allow-half />
              <span style="color:var(--t3);">{{ (score / 20).toFixed(1) }} / 5 · 评级：{{ grade }}</span>
            </div>
            <h4 style="margin:0 0 8px;">整体评语</h4>
            <p style="color:var(--t2);line-height:1.9;margin:0;">{{ report.evaluation.overall_comment }}</p>
          </div>
          <div class="report-actions" style="width:220px;display:flex;flex-direction:column;gap:12px;">
            <a-button type="primary" size="large" :loading="downloading" @click="downloadPdf">
              {{ downloading ? '生成中…' : '⬇ 下载 PDF 报告' }}
            </a-button>
            <a-button type="primary" size="large" @click="$router.push('/config')">再练一场</a-button>
            <a-button size="large" @click="$router.push('/')">返回首页</a-button>
            <a-button size="large" @click="share">分享成绩</a-button>
            <p v-if="!report.is_member" style="font-size:12px;color:var(--t3);text-align:center;margin:0;">
              会员可解锁五维报告与逐题复盘
              <a @click="$router.push('/pricing')" style="color:var(--orange);cursor:pointer;">开通 →</a>
            </p>
          </div>
        </div>
      </a-card>

      <!-- 会员深度报告 -->
      <div style="position:relative;">
        <div style="display:flex;gap:20px;flex-wrap:wrap;">
          <a-card v-if="report.dimensions.length" style="flex:1;min-width:320px;border-radius:14px;" :bordered="false">
            <h3 style="margin-top:0;">能力维度评分</h3>
            <div v-for="d in report.dimensions" :key="d.dimension"
                 style="display:flex;align-items:center;gap:12px;padding:8px 0;">
              <span style="width:70px;font-size:14px;">{{ d.name }}</span>
              <a-progress :percent="d.score" :show-info="false" :stroke-color="d.score < 70 ? '#FF7A45' : '#3B5BFF'"
                          style="flex:1;margin:0;" />
              <b :style="{ color: d.score < 70 ? 'var(--orange)' : 'var(--t1)' }">{{ d.score }}</b>
            </div>
            <a-divider />
            <p v-for="d in report.dimensions" :key="d.dimension" style="font-size:13px;color:var(--t2);margin:4px 0;">
              · {{ d.name }}：{{ d.feedback }}
            </p>
          </a-card>

          <a-card v-if="report.question_evaluations.length" style="flex:1.3;min-width:360px;border-radius:14px;" :bordered="false">
            <h3 style="margin-top:0;">逐题复盘（{{ report.question_evaluations.length }} 题）</h3>
            <p style="font-size:12px;color:var(--t3);margin:0 0 10px;">点击任意一行查看完整复盘详情</p>
            <a-table :columns="qCols" :data-source="report.question_evaluations" :pagination="false" size="small"
                     :custom-row="qRow" :row-key="(r) => r.title">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'score'">
                  <b :style="{ color: record.score < 70 ? 'var(--orange)' : 'var(--green)' }">{{ record.score }}</b>
                </template>
                <template v-else-if="column.key === 'title'">
                  <a style="color:var(--t1);">{{ record.title }}</a>
                </template>
              </template>
            </a-table>
          </a-card>
        </div>

        <!-- 非会员遮罩 -->
        <div v-if="!report.is_member" class="lock-mask">
          <span style="font-size:36px;">🔒</span>
          <p style="font-size:17px;font-weight:700;margin:0;">会员深度报告已锁定</p>
          <p style="color:var(--t2);font-size:13px;margin:0;line-height:1.8;">
            能力维度评分 + 逐题复盘 + 改进建议已为你生成。<br />开通会员即可解锁，并解锁每月不限次模拟面试。
          </p>
          <div style="display:flex;gap:12px;">
            <button class="btn-unlock" @click="$router.push('/pricing')">立即解锁 ¥39 起</button>
          </div>
        </div>
      </div>

      <!-- 环节回顾 -->
      <a-card style="border-radius:14px;margin-top:20px;" :bordered="false">
        <h3 style="margin-top:0;">环节回顾</h3>
        <a-table :columns="secCols" :data-source="sectionReview" :pagination="false" size="small" row-key="name" />
        <div style="display:flex;gap:20px;padding-top:10px;">
          <a @click="downloadJson" style="color:var(--primary);cursor:pointer;">⬇ 下载面试数据（JSON）</a>
          <a @click="deleteLocal" style="color:var(--red);cursor:pointer;">删除本场本地数据</a>
        </div>
      </a-card>
    </div>

    <!-- 逐题复盘详情抽屉 -->
    <a-drawer v-model:open="detailOpen" :title="detailQ?.title" width="460" placement="right">
      <template v-if="detailQ">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:16px;flex-wrap:wrap;">
          <a-tag color="blue">{{ detailSection || '面试题' }}</a-tag>
          <a-tag>{{ TYPE_LABELS[detailQ.type] || '技术问题' }}</a-tag>
          <b :style="{ color: detailQ.score < 70 ? 'var(--orange)' : 'var(--green)', fontSize: '18px' }">
            {{ detailQ.score }} 分
          </b>
        </div>
        <template v-if="detailContent">
          <h4 class="drawer-h">原题</h4>
          <p class="drawer-text">{{ detailContent }}</p>
        </template>
        <h4 class="drawer-h">AI 点评</h4>
        <p class="drawer-text">{{ detailQ.feedback || '暂无' }}</p>
        <h4 class="drawer-h">改进建议</h4>
        <p class="drawer-text">{{ detailQ.suggestion || '暂无' }}</p>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import RoomHeader from '../components/RoomHeader.vue'
import { useInterviewStore } from '../stores/interview'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const store = useInterviewStore()
const userStore = useUserStore()
const report = ref(null)
const reportBody = ref(null)
const downloading = ref(false)
const capturing = ref(false)

const score = computed(() => report.value?.evaluation?.total_score || 0)
const grade = computed(() => (score.value >= 88 ? '优秀' : score.value >= 75 ? '进阶' : '扎实'))

const qCols = [
  { title: '题目', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '得分', dataIndex: 'score', key: 'score', width: 60 },
  { title: 'AI 点评', dataIndex: 'feedback', key: 'feedback', ellipsis: true },
  { title: '改进建议', dataIndex: 'suggestion', key: 'suggestion', ellipsis: true },
]

const TYPE_LABELS = {
  fundamental: '技术八股', project_dig: '项目深挖', behavioral: '行为面试',
  algorithm: '算法题', system_design: '系统设计', coding: '在线编程', whiteboard: '白板设计',
}

// ---------- 逐题复盘详情抽屉 ----------
const detailOpen = ref(false)
const detailQ = ref(null)

// 按标题关联回会话题目，补充原题内容与所属环节
const detailContent = computed(() => findQuestion(detailQ.value?.title)?.snapshot?.content || '')
const detailSection = computed(() => SECTION_NAMES[findQuestion(detailQ.value?.title)?.section_type] || '')

function findQuestion(title) {
  if (!title) return null
  return (report.value?.session?.questions || []).find((q) => q.snapshot?.title === title) || null
}

function openDetail(record) {
  detailQ.value = record
  detailOpen.value = true
}

// 行可点击，光标提示
const qRow = (record) => ({ onClick: () => openDetail(record), style: { cursor: 'pointer' } })
const secCols = [
  { title: '环节', dataIndex: 'name', key: 'name', width: 120 },
  { title: '内容', dataIndex: 'content', key: 'content' },
  { title: '完成状态', dataIndex: 'status', key: 'status', width: 160 },
]

const SECTION_NAMES = { voice: '语音问答', coding: '在线编程', whiteboard: '白板设计' }
const sectionReview = computed(() => {
  const s = report.value?.session
  if (!s) return []
  return (s.sections || []).map((sec) => ({
    name: SECTION_NAMES[sec.section_type] || sec.section_type,
    content: `${(s.questions || []).filter((q) => q.section_type === sec.section_type).length} 题`,
    status: '✓ 已完成',
  }))
})

function share() {
  const text = `我在 AI 模拟面试助手中拿到 ${score.value} 分（${grade.value}），快来挑战一场真实的技术面试吧！`
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => message.success('成绩文案已复制到剪贴板'))
  } else {
    message.info(text)
  }
}

function downloadJson() {
  const data = JSON.stringify(report.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `interview-report-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}

/** 将报告区域导出为 PDF（html2canvas 截图 + jsPDF 分页，所见即所得） */
async function downloadPdf() {
  if (!reportBody.value || downloading.value) return
  downloading.value = true
  capturing.value = true
  try {
    // 等按钮隐藏后再截图，避免操作按钮出现在 PDF 里
    await nextTick()
    const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
      import('html2canvas'),
      import('jspdf'),
    ])
    const el = reportBody.value
    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#F7F8FA',
      // 只截取报告主体，忽略固定定位的顶栏
      ignoreElements: (node) => node.classList?.contains('room-bar'),
    })
    const pdf = new jsPDF('p', 'mm', 'a4')
    const pageW = 210
    const pageH = 297
    const margin = 6
    const imgW = pageW - margin * 2
    const imgH = (canvas.height * imgW) / canvas.width
    const imgData = canvas.toDataURL('image/jpeg', 0.92)
    // 一页放不下时分页，每页向上错位一页高度
    if (imgH <= pageH - margin * 2) {
      pdf.addImage(imgData, 'JPEG', margin, margin, imgW, imgH)
    } else {
      let remaining = imgH
      let offset = 0
      while (remaining > 0) {
        pdf.addImage(imgData, 'JPEG', margin, margin - offset, imgW, imgH)
        remaining -= pageH - margin * 2
        offset += pageH - margin * 2
        if (remaining > 0) pdf.addPage()
      }
    }
    const pos = report.value.session.position?.name || '面试'
    pdf.save(`面试报告-${pos}-${score.value}分.pdf`)
    message.success('PDF 报告已生成并开始下载')
  } catch (e) {
    console.error(e)
    message.error('PDF 生成失败，请重试')
  } finally {
    capturing.value = false
    downloading.value = false
  }
}

function deleteLocal() {
  store.reset()
  message.success('本地面试数据已清除')
  router.push('/')
}

onMounted(async () => {
  // 支持 /report?session={id}（新标签页查看历史报告）与 ?download=1（自动下载 PDF）
  const sessionId = route.query.session
  try {
    if (!store.report && sessionId) {
      await store.loadServerReport(sessionId)
    }
  } catch (e) {
    message.error('报告加载失败')
    return router.replace('/')
  }
  if (store.report) {
    report.value = store.report
    if (route.query.download === '1') {
      await nextTick()
      downloadPdf()
    }
  } else {
    router.replace('/config')
  }
})
</script>

<style scoped>
/* 生成 PDF 截图时隐藏操作按钮区，避免按钮出现在 PDF 中 */
.report-body.capturing .report-actions {
  visibility: hidden;
}

/* 逐题复盘详情抽屉 */
.drawer-h {
  margin: 18px 0 6px;
  color: var(--t2);
  font-size: 14px;
}
.drawer-text {
  margin: 0;
  line-height: 1.9;
  white-space: pre-wrap;
  color: var(--t1);
  font-size: 13.5px;
}

/* 逐题复盘表格行可点击的悬浮反馈 */
:deep(.ant-table-tbody > tr.ant-table-row) {
  transition: background-color .15s ease;
}
:deep(.ant-table-tbody > tr.ant-table-row:hover > td) {
  background: #F0F4FF !important;
}
</style>
