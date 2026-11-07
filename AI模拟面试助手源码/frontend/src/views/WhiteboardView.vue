<template>
  <div>
    <RoomHeader :current="2" @pause="() => {}" />

    <div class="room-body">
      <div class="q-card" style="margin-bottom:16px;">
        <div>
          <p class="q-eyebrow">第 1 / {{ whiteboardQuestions.length }} 题 · 系统设计 · 边讲边画</p>
          <h2 class="q-title">{{ currentQ?.snapshot?.title }}</h2>
          <p style="color:var(--t2);line-height:1.8;margin:10px 0 0;">{{ currentQ?.snapshot?.content }}</p>
        </div>
        <span class="tag-grey">📐 边讲边画</span>
      </div>

      <div style="display:flex;gap:16px;height:520px;">
        <!-- 工具栏 -->
        <div style="display:flex;flex-direction:column;gap:8px;background:#fff;border:1px solid var(--line2);border-radius:12px;padding:10px 8px;">
          <div class="tool-btn" :class="{ on: tool === 'select' }" title="选择/拖拽" @click="tool = 'select'">🖱️</div>
          <div class="tool-btn" :class="{ on: tool === 'connect' }" title="连线（依次点击两个节点）" @click="startConnect">🔗</div>
          <div style="height:1px;background:var(--line);margin:2px 0;" />
          <div v-for="el in elements" :key="el.emoji" class="tool-btn" :title="el.title"
               @click="addNode(el)">{{ el.emoji }}</div>
          <div style="height:1px;background:var(--line);margin:2px 0;" />
          <div class="tool-btn" title="删除选中" @click="deleteSelected">🗑️</div>
          <div class="tool-btn" title="清空画布" @click="clearAll">🧹</div>
        </div>

        <!-- 画布 -->
        <div ref="canvasWrap" style="flex:1;position:relative;border-radius:12px;overflow:hidden;border:1px solid var(--line2);">
          <div class="board-art" ref="board">
            <svg style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;">
              <line v-for="(e, i) in store.whiteboard.edges" :key="i"
                    :x1="nodeCenter(e.from).x" :y1="nodeCenter(e.from).y"
                    :x2="nodeCenter(e.to).x" :y2="nodeCenter(e.to).y"
                    stroke="#3B5BFF" stroke-width="2" marker-end="url(#arrow)" />
              <defs>
                <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                  <path d="M0,0 L7,3 L0,6 Z" fill="#3B5BFF" />
                </marker>
              </defs>
            </svg>
            <div v-for="n in store.whiteboard.nodes" :key="n.id" class="wb-node"
                 :class="{ sel: selectedId === n.id, conn: connectFrom === n.id }"
                 :style="{ left: n.x + 'px', top: n.y + 'px' }"
                 @mousedown.stop="onNodeMouseDown($event, n)" @click.stop="onNodeClick(n)">
              <span class="em">{{ n.emoji }}</span>
              <span>{{ n.label }}<small v-if="n.role" class="role">· {{ n.role }}</small></span>
            </div>
          </div>
          <div style="position:absolute;right:12px;bottom:10px;font-size:12px;color:var(--t3);background:rgba(255,255,255,.85);padding:4px 10px;border-radius:6px;">
            元素 {{ store.whiteboard.nodes.length }} · 连线 {{ store.whiteboard.edges.length }} · {{ savedTip }}
          </div>
          <div v-if="tool === 'connect'" style="position:absolute;left:12px;top:12px;"
               class="note-strip">🔗 连线模式：依次点击起点与终点节点</div>
        </div>

        <!-- AI 观察面板 -->
        <a-card style="width:280px;flex:none;border-radius:12px;" :bordered="false" :body-style="{ padding: '16px' }">
          <h4 style="margin:0 0 12px;">🤖 AI 面试官观察</h4>
          <p style="font-size:13px;color:var(--t2);line-height:1.8;margin:0 0 10px;">
            · 正在观察你的架构图与讲解<br/>
            · 已识别关键词：<b style="color:var(--primary);">{{ detectedKeywords.join('、') || '暂无' }}</b>
          </p>
          <a-alert v-for="fu in followups" :key="fu" type="warning" style="margin-bottom:10px;font-size:12px;"
                   :message="fu" show-icon />
          <div class="note-strip" style="font-size:12px;">
            💡 讲解要点：先讲清整体链路，再补「缓存一致性 + 容量估算」，最后收尾到监控与降级。
          </div>
          <a-textarea v-model:value="explanation" :rows="4" placeholder="画完后，在这里（或开麦）讲解你的设计思路…"
                      style="margin-top:12px;" />
          <a-button type="primary" block size="large" style="height:42px;margin-top:12px;" :loading="finishing"
                    @click="finish">完成讲解，结束面试</a-button>
          <p style="font-size:12px;color:var(--t3);text-align:center;margin:8px 0 0;">点击后 AI 将生成整场评分报告</p>
        </a-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import RoomHeader from '../components/RoomHeader.vue'
import { useInterviewStore } from '../stores/interview'

const router = useRouter()
const store = useInterviewStore()

const elements = [
  { emoji: '🧑‍💻', label: '用户', title: '用户' },
  { emoji: '☁️', label: '负载均衡', title: '负载均衡' },
  { emoji: '🛣️', label: 'API 网关', title: '网关' },
  { emoji: '🧩', label: '微服务', title: '微服务' },
  { emoji: '⚡', label: 'Redis 缓存', title: '缓存' },
  { emoji: '🗄️', label: '数据库', title: '数据库' },
  { emoji: '📮', label: '消息队列', title: '消息队列' },
]

const tool = ref('select')
const selectedId = ref(null)
const connectFrom = ref(null)
const explanation = ref('')
const finishing = ref(false)
const savedTip = ref('自动暂存中')
const board = ref(null)

const whiteboardQuestions = computed(() => store.questionsBySection.whiteboard || [])
const currentQ = computed(() => whiteboardQuestions.value[0])

const detectedKeywords = computed(() => {
  const kws = ['缓存', '分片', '消息队列', '限流', '网关', '主从', '降级']
  const text = store.whiteboard.nodes.map((n) => n.label).join(' ') + ' ' + explanation.value
  return kws.filter((k) => text.includes(k))
})

const followups = computed(() => {
  const list = []
  if (store.whiteboard.nodes.some((n) => n.label.includes('缓存'))) {
    list.push('追问 1：缓存未命中怎么办？如何保证缓存与数据库一致性？')
  }
  if (store.whiteboard.nodes.length >= 5) {
    list.push('追问 2：流量再涨 10 倍，哪个组件最先成为瓶颈？')
  }
  return list
})

let idSeq = 1
function addNode(el) {
  const rect = board.value?.getBoundingClientRect()
  const x = 80 + ((idSeq * 60) % Math.max((rect?.width || 600) - 200, 100))
  const y = 60 + ((idSeq * 70) % 340)
  store.whiteboard.nodes.push({ id: `n${idSeq++}`, emoji: el.emoji, label: el.label, x, y })
  tool.value = 'select'
  scheduleSave()
}

function startConnect() {
  tool.value = 'connect'
  connectFrom.value = null
}

function onNodeClick(n) {
  if (tool.value !== 'connect') return
  if (!connectFrom.value) {
    connectFrom.value = n.id
  } else if (connectFrom.value !== n.id) {
    store.whiteboard.edges.push({ from: connectFrom.value, to: n.id })
    connectFrom.value = null
    scheduleSave()
  }
}

function nodeCenter(id) {
  const n = store.whiteboard.nodes.find((x) => x.id === id)
  if (!n) return { x: 0, y: 0 }
  return { x: n.x + 40, y: n.y + 20 }
}

/* ---------- 拖拽 ---------- */
let dragging = null
function onNodeMouseDown(e, n) {
  if (tool.value === 'connect') return
  selectedId.value = n.id
  dragging = { node: n, startX: e.clientX, startY: e.clientY, origX: n.x, origY: n.y }
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}
function onMouseMove(e) {
  if (!dragging) return
  dragging.node.x = dragging.origX + (e.clientX - dragging.startX)
  dragging.node.y = dragging.origY + (e.clientY - dragging.startY)
}
function onMouseUp() {
  if (dragging) scheduleSave()
  dragging = null
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})

function deleteSelected() {
  if (!selectedId.value) return message.info('先点击选中一个节点')
  store.whiteboard.nodes = store.whiteboard.nodes.filter((n) => n.id !== selectedId.value)
  store.whiteboard.edges = store.whiteboard.edges.filter(
    (e) => e.from !== selectedId.value && e.to !== selectedId.value)
  selectedId.value = null
  scheduleSave()
}

function clearAll() {
  store.whiteboard.nodes = []
  store.whiteboard.edges = []
  scheduleSave()
}

/* ---------- 自动保存 ---------- */
let saveTimer = null
function scheduleSave() {
  savedTip.value = '自动暂存中…'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(async () => {
    await store.saveWhiteboard({ nodes: store.whiteboard.nodes, edges: store.whiteboard.edges })
    savedTip.value = `✔ 已自动保存 ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`
  }, 1200)
}

async function finish() {
  finishing.value = true
  try {
    if (explanation.value.trim()) store.recordExplanation(currentQ.value, explanation.value)
    await store.saveWhiteboard({ nodes: store.whiteboard.nodes, edges: store.whiteboard.edges })
    store._persist()
    await store.finish()
    store._clearPersist()
    message.success('面试已结束，正在生成评分报告…')
    router.push('/report')
  } catch (e) {
    message.error(e.message || '生成报告失败')
  } finally { finishing.value = false }
}

onMounted(() => {
  store._restore()
  if (!store.session) return router.replace('/config')
  if (!whiteboardQuestions.value.length) {
    // 无白板题：直接评分
    store.finish().then(() => router.replace('/report'))
  }
})
</script>
