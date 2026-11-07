<template>
  <div>
    <RoomHeader :current="0" @pause="onPause" />

    <div class="room-body">
      <div class="note-strip" style="margin-bottom:16px;">
        <b>语音问答环节：</b>请直接开口回答；不方便开麦时可点击「改用文字作答」。AI 面试官会针对你的回答持续追问。
        <a-switch v-model:checked="ttsOn" size="small" style="margin-left:12px;" />
        <span style="font-size:12px;color:var(--t3);">语音播报</span>
      </div>

      <!-- 当前题目 -->
      <div class="q-card" style="margin-bottom:16px;">
        <div>
          <p class="q-eyebrow">
            第 <b style="color:var(--primary);">{{ qIndex + 1 }}</b> / {{ voiceQuestions.length }} 题 ·
            {{ typeLabel(currentQ?.snapshot?.type) }} ·
            <a-tag :color="['green','blue','orange'][difficultyIdx]" size="small" style="margin-left:4px;">难度 {{ currentQ?.snapshot?.difficulty || 1 }}</a-tag>
          </p>
          <h2 class="q-title">{{ currentQ?.snapshot?.title }}</h2>
          <p style="color:var(--t2);line-height:1.8;margin:10px 0 0;">{{ currentQ?.snapshot?.content }}</p>
        </div>
        <span class="tag-grey">💬 请语音回答</span>
      </div>

      <!-- 对话区 -->
      <div ref="chatBox" style="background:#fff;border:1px solid var(--line2);border-radius:12px;padding:20px;height:380px;overflow-y:auto;">
        <div v-for="(m, i) in store.voiceChat" :key="i"
             :style="{ display:'flex', justifyContent: m.role === 'candidate' ? 'flex-end' : 'flex-start', marginBottom: 14 }">
          <div :style="{
            maxWidth: '78%', padding: '12px 16px', borderRadius: 12, lineHeight: 1.8, fontSize: 14,
            background: m.role === 'candidate' ? '#EBEFFF' : '#F7F8FA',
          }">
            <p style="font-size:11px;color:var(--t3);margin:0 0 6px;">
              {{ m.role === 'candidate' ? '我' : 'AI 面试官' }}{{ m.meta ? ` · ${m.meta}` : '' }}
            </p>
            <p style="margin:0;white-space:pre-wrap;">{{ m.text }}</p>
          </div>
        </div>
        <div v-if="aiThinking" style="display:flex;gap:8px;align-items:center;color:var(--t3);font-size:13px;">
          <a-spin size="small" /> AI 正在分析你的回答 · 准备追问…
        </div>
      </div>

      <!-- 底部控制条 -->
      <div style="background:#fff;border:1px solid var(--line2);border-radius:12px;margin-top:16px;padding:14px 20px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
        <a-button :type="recording ? 'primary' : 'default'" shape="circle" size="large"
                  :style="recording ? 'background:var(--red);border-color:var(--red);' : ''"
                  @click="toggleMic">
          <template #icon>
            <span style="font-size:16px;">{{ recording ? '⏹' : '🎤' }}</span>
          </template>
        </a-button>
        <span style="font-size:13px;color:var(--t3);width:88px;">{{ recording ? '正在聆听…' : '点击开麦回答' }}</span>
        <a-input v-model:value="draft" placeholder="或在此输入文字回答…" style="flex:1;min-width:200px;"
                 @pressEnter="sendText" />
        <a-button type="primary" :loading="aiThinking" @click="sendText">发送回答</a-button>
        <a-button @click="skipQuestion">跳过本题</a-button>
        <a-button type="primary" ghost @click="nextSection" style="margin-left:auto;">下一环节 →</a-button>
        <a-popconfirm title="确定结束整场面试吗？" @confirm="finishEarly">
          <a-button danger type="text">结束面试</a-button>
        </a-popconfirm>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import RoomHeader from '../components/RoomHeader.vue'
import { useInterviewStore } from '../stores/interview'

const router = useRouter()
const store = useInterviewStore()

const chatBox = ref(null)
const draft = ref('')
const aiThinking = ref(false)
const recording = ref(false)
const ttsOn = ref(true)
const qIndex = ref(0)
const followupNo = ref(0)

const voiceQuestions = computed(() => store.questionsBySection.voice || [])
const currentQ = computed(() => voiceQuestions.value[qIndex.value])
const difficultyIdx = computed(() => Math.min((currentQ.value?.snapshot?.difficulty || 1) - 1, 2))

const TYPE_LABELS = { fundamental: '技术八股', project_dig: '项目深挖', behavioral: '行为面试', algorithm: '算法题', system_design: '系统设计' }
const typeLabel = (t) => TYPE_LABELS[t] || '技术问题'

/* ---------- TTS 播报 ---------- */
function speak(text) {
  if (!ttsOn.value || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.lang = 'zh-CN'
  u.rate = 1.05
  window.speechSynthesis.speak(u)
}

function pushAI(text) {
  store.voiceChat.push({ role: 'interviewer', text, meta: '语音' })
  speak(text)
}

/* ---------- 语音识别（Web Speech API） ---------- */
let recognition = null
function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SR) return null
  const r = new SR()
  r.lang = 'zh-CN'
  r.continuous = true
  r.interimResults = false
  r.onresult = (e) => {
    let text = ''
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) text += e.results[i][0].transcript
    }
    if (text) draft.value = (draft.value + ' ' + text).trim()
  }
  r.onerror = (e) => {
    if (e.error !== 'no-speech' && e.error !== 'aborted') {
      message.warning(`语音识别异常（${e.error}），可改用文字作答`)
    }
  }
  r.onend = () => { recording.value = false }
  return r
}
function toggleMic() {
  if (!recognition) {
    recognition = initRecognition()
    if (!recognition) return message.warning('当前浏览器不支持语音识别（建议 Chrome/Edge），请使用文字作答')
  }
  if (recording.value) {
    recognition.stop()
    recording.value = false
  } else {
    try {
      recognition.start()
      recording.value = true
    } catch { /* 已在录音中 */ }
  }
}
onUnmounted(() => recognition?.stop?.())

/* ---------- 回答与追问 ---------- */
async function sendText() {
  const text = draft.value.trim()
  if (!text) return message.warning('请先输入或说出你的回答')
  if (aiThinking.value) return
  draft.value = ''
  store.voiceChat.push({ role: 'candidate', text, meta: recording.value ? '语音转写' : '文字' })
  aiThinking.value = true
  try {
    const reply = await store.sendAnswer(currentQ.value, text, followupNo.value)
    pushAI(reply.reply)
    if (reply.is_followup) {
      followupNo.value += 1
    } else {
      goNextQuestion()
    }
  } catch (e) {
    message.error(e.message || '网络异常，请重试')
  } finally {
    aiThinking.value = false
    scrollToBottom()
  }
}

function goNextQuestion() {
  followupNo.value = 0
  if (qIndex.value < voiceQuestions.value.length - 1) {
    qIndex.value += 1
    const q = currentQ.value
    setTimeout(() => pushAI(`好的，我们来看第 ${qIndex.value + 1} 题：${q.snapshot.title}。${q.snapshot.content}`), 600)
  } else {
    setTimeout(() => pushAI('语音问答环节到此结束，整体回答得不错。接下来我们进入在线编程环节，请准备好。'), 600)
  }
}

function skipQuestion() {
  store.recordSkip(currentQ.value)
  goNextQuestion()
}

function scrollToBottom() {
  nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight })
}

function nextSection() {
  store.currentSection = store.questionsBySection.coding.length ? 'coding' : 'whiteboard'
  store._persist()
  router.push(store.questionsBySection.coding.length ? '/room/coding' : '/room/whiteboard')
}

async function finishEarly() {
  await store.finish()
  router.push('/report')
}

function onPause() {
  if (window.speechSynthesis?.speaking) window.speechSynthesis.pause()
  message.info('已暂停，点击麦克风或发送继续')
}

onMounted(() => {
  store._restore()
  if (!store.session) return router.replace('/config')
  const q = currentQ.value
  if (q) {
    store.voiceChat.push({
      role: 'interviewer',
      text: `你好，我是本场模拟面试的 AI 面试官，接下来是语音问答环节，共 ${voiceQuestions.value.length} 题。第 1 题：${q.snapshot.title}。${q.snapshot.content}`,
      meta: '开场白',
    })
    speak(store.voiceChat[0].text)
  } else {
    nextSection()
  }
})
</script>
