<template>
  <div class="room-bar">
    <div style="display:flex;align-items:center;min-width:0;">
      <div class="rb-brand">
        <span class="logo-mark" style="width:28px;height:28px;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" fill="#fff"/></svg>
        </span>
        <span>AI 模拟面试 · {{ store.session?.position?.name || '面试房间' }}</span>
        <i v-if="!finished" class="rb-live"></i>
      </div>
      <div class="rb-steps">
        <div v-for="(s, i) in steps" :key="s.key" class="rb-step">
          <span class="rb-dot" :class="{ on: current === i && !finished, done: current > i || finished }">
            {{ current > i || finished ? '✓' : i + 1 }}
          </span>
          <span class="rb-tx" :class="{ on: current === i && !finished, done: current > i || finished }">{{ s.label }}</span>
        </div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:16px;">
      <span class="rb-time" :class="{ warn: remainingMin < 5 }">{{ remainingText }}</span>
      <a-button v-if="!finished" type="default" size="small" @click="emit('pause')">暂停</a-button>
      <span v-else style="color:var(--green);font-weight:600;">✓ 本场面试已结束</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useInterviewStore } from '../stores/interview'

const props = defineProps({
  current: { type: Number, required: true },
  finished: { type: Boolean, default: false },
})
const emit = defineEmits(['pause'])
const store = useInterviewStore()

const steps = [
  { key: 'voice', label: '语音问答' },
  { key: 'coding', label: '在线编程' },
  { key: 'whiteboard', label: '白板设计' },
  { key: 'report', label: '评分反馈' },
]

const now = ref(Date.now())
let timer = null
onMounted(() => { timer = setInterval(() => (now.value = Date.now()), 1000) })
onUnmounted(() => clearInterval(timer))

const remainingSec = computed(() => {
  const total = (store.session?.durationMin || 45) * 60
  const used = Math.floor((now.value - (store.startedAt || Date.now())) / 1000)
  return Math.max(0, total - used)
})
const remainingMin = computed(() => Math.floor(remainingSec.value / 60))
const remainingText = computed(() => {
  const s = remainingSec.value
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})
</script>
