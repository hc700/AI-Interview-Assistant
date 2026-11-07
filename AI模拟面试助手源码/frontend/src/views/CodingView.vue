<template>
  <div>
    <RoomHeader :current="1" @pause="() => {}" />

    <div class="room-body">
      <div class="note-strip" style="margin-bottom:16px;">
        <b>在线编程环节：</b>请完成右侧代码并运行用例，随后口头/文字讲解你的<b>思路与复杂度</b>。AI 面试官会就你的代码进行追问。
      </div>

      <div style="display:flex;gap:16px;flex-wrap:wrap;">
        <!-- 左侧题目面板 -->
        <a-card style="flex:1;min-width:320px;border-radius:12px;" :bordered="false">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <h2 style="margin:0;font-size:18px;">{{ currentQ?.snapshot?.title }}</h2>
            <a-tag v-for="t in currentQ?.snapshot?.tags || []" :key="t" color="blue">{{ t }}</a-tag>
            <a-tag :color="['green','orange','red'][difficultyIdx]">
              {{ ['初级', '中级', '高级'][difficultyIdx] }}
            </a-tag>
          </div>
          <p style="color:var(--t2);line-height:1.9;margin:14px 0;">{{ currentQ?.snapshot?.content }}</p>
          <a-divider style="margin:12px 0;" />
          <p style="font-weight:600;margin:0 0 8px;">测试用例（{{ passedCount }} / {{ totalCases }} 通过）</p>
          <div v-for="(c, i) in caseRows" :key="i"
               style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:var(--bg);border-radius:8px;margin-bottom:6px;font-size:12px;">
            <span :style="{ color: c.ok ? 'var(--green)' : 'var(--red)', fontWeight: 700 }">{{ c.ok ? '✓' : '✗' }}</span>
            <code style="font-family:Consolas,monospace;">{{ c.input }}</code>
            <span style="margin-left:auto;color:var(--t3);">→ {{ c.expected }}</span>
          </div>
        </a-card>

        <!-- 右侧代码编辑器 -->
        <div style="flex:1.2;min-width:360px;background:#fff;border:1px solid var(--line2);border-radius:12px;overflow:hidden;display:flex;flex-direction:column;">
          <div style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--line2);">
            <b style="font-family:Consolas,monospace;">Solution.{{ langExt }}</b>
            <a-select v-model:value="language" size="small" style="width:130px;margin-left:auto;"
                      :options="langOptions" />
          </div>
          <div style="display:flex;background:#1E1E2E;min-height:300px;flex:1;">
            <div style="padding:14px 8px;text-align:right;color:#6C7086;font-family:Consolas,monospace;font-size:13px;line-height:1.7;user-select:none;">
              <div v-for="n in lineCount" :key="n">{{ n }}</div>
            </div>
            <textarea v-model="code" spellcheck="false"
                      style="flex:1;background:transparent;border:none;outline:none;resize:vertical;color:#D4D8E8;padding:14px 12px;font-family:Consolas,monospace;font-size:13px;line-height:1.7;min-height:300px;" />
          </div>
          <div v-if="runResult" style="padding:12px 16px;background:#F7F8FA;border-top:1px solid var(--line2);font-size:13px;">
            <p style="margin:0 0 4px;font-family:Consolas,monospace;color:var(--t3);">
              $ 运行 {{ language }} Solution
            </p>
            <p style="margin:0;" :style="{ color: runResult.passed === runResult.total ? 'var(--green)' : 'var(--orange)' }">
              {{ runResult.output }}
            </p>
          </div>
          <div style="display:flex;gap:12px;align-items:center;padding:14px 16px;border-top:1px solid var(--line2);flex-wrap:wrap;">
            <a-button :loading="running" @click="runCode">▶ 运行代码</a-button>
            <a-button type="primary" @click="submitAndExplain">提交并讲解思路</a-button>
            <span style="font-size:12px;color:var(--t3);">代码已自动暂存 {{ lastSaved }}</span>
            <a-button type="primary" ghost style="margin-left:auto;" @click="nextStep">
              {{ isLastCoding ? '进入白板环节 →' : '下一题 →' }}
            </a-button>
          </div>
        </div>
      </div>

      <!-- 讲解思路 -->
      <a-modal v-model:open="explainOpen" title="口头讲解思路" @ok="confirmExplain" ok-text="提交讲解" cancel-text="稍后再说">
        <p style="color:var(--t2);">AI 面试官：代码我看到了。请讲讲你的<b>解题思路与时间/空间复杂度</b>，面试中主动说明复杂度是重要加分项。</p>
        <a-textarea v-model:value="explanation" :rows="5"
                    placeholder="例如：使用哈希表一次遍历，时间复杂度 O(n)，空间复杂度 O(n)……" />
      </a-modal>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import RoomHeader from '../components/RoomHeader.vue'
import { useInterviewStore } from '../stores/interview'

const router = useRouter()
const store = useInterviewStore()

const langOptions = [
  { value: 'python', label: 'Python 3' },
  { value: 'java', label: 'Java 17' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'go', label: 'Go' },
]
const TEMPLATES = {
  python: 'class Solution:\n    def solve(self, nums):\n        # 在此实现你的解法\n        return nums\n',
  java: 'class Solution {\n    public int[] solve(int[] nums) {\n        // 在此实现你的解法\n        return nums;\n    }\n}\n',
  javascript: '/**\n * @param {number[]} nums\n * @return {number[]}\n */\nvar solve = function(nums) {\n    return nums;\n};\n',
  go: 'func solve(nums []int) []int {\n    // 在此实现你的解法\n    return nums\n}\n',
}

const language = ref('python')
const code = ref(TEMPLATES.python)
const qIndex = ref(0)
const running = ref(false)
const runResult = ref(null)
const explainOpen = ref(false)
const explanation = ref('')
const lastSaved = ref('')

const codingQuestions = computed(() => store.questionsBySection.coding || [])
const currentQ = computed(() => codingQuestions.value[qIndex.value])
const difficultyIdx = computed(() => Math.min((currentQ.value?.snapshot?.difficulty || 1) - 1, 2))
const isLastCoding = computed(() => qIndex.value >= codingQuestions.value.length - 1)
const caseRows = computed(() => {
  const cases = currentQ.value?.snapshot?.test_cases || []
  const result = runResult.value?.cases
  if (result) return result
  return cases.map((c) => ({ input: c.input, expected: c.expected, ok: null }))
})
const passedCount = computed(() => caseRows.value.filter((c) => c.ok).length)
const totalCases = computed(() => caseRows.value.length)
const langExt = computed(() => ({ python: 'py', java: 'java', javascript: 'js', go: 'go' }[language.value]))
const lineCount = computed(() => code.value ? code.value.split('\n').length : 0)

watch(language, (l) => { if (!code.value.trim() || Object.values(TEMPLATES).includes(code.value)) code.value = TEMPLATES[l] })
watch(code, () => { lastSaved.value = new Date().toLocaleTimeString('zh-CN', { hour12: false }) })

async function runCode() {
  if (!code.value.trim()) return message.warning('请先编写代码')
  running.value = true
  try {
    runResult.value = await store.submitCode(currentQ.value, language.value, code.value)
    if (runResult.value.passed === runResult.value.total) {
      message.success('全部用例通过！记得口头讲解思路')
    } else {
      message.warning(`通过 ${runResult.value.passed}/${runResult.value.total} 个用例`)
    }
  } catch (e) {
    message.error(e.message || '运行失败')
  } finally { running.value = false }
}

function submitAndExplain() {
  if (!runResult.value) {
    message.info('先运行一次代码再提交讲解吧')
    return runCode()
  }
  explainOpen.value = true
}

async function confirmExplain() {
  if (explanation.value.trim()) {
    store.recordExplanation(currentQ.value, explanation.value.trim())
  }
  explainOpen.value = false
  message.success('提交成功。讲解已计入评分依据')
}

function nextStep() {
  if (!isLastCoding.value) {
    qIndex.value += 1
    runResult.value = null
    explanation.value = ''
    store._persist()
    message.info(`进入第 ${qIndex.value + 1} 道编程题`)
  } else {
    store.currentSection = store.questionsBySection.whiteboard.length ? 'whiteboard' : 'report'
    store._persist()
    router.push(store.questionsBySection.whiteboard.length ? '/room/whiteboard' : '/report')
  }
}

onMounted(() => {
  store._restore()
  if (!store.session) return router.replace('/config')
  if (!codingQuestions.value.length) {
    router.replace(store.questionsBySection.whiteboard.length ? '/room/whiteboard' : '/report')
  }
})
</script>
