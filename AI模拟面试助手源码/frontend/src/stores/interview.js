import { defineStore } from 'pinia'
import api from '../api'
import { useUserStore } from './user'

/**
 * 面试会话 store：登录用户走后端（落库、消耗配额），
 * 游客走本地模式（公开出题接口 + localStorage 记录）。
 */
export const useInterviewStore = defineStore('interview', {
  state: () => ({
    // 会话配置
    session: null, // { id, isGuest, position, difficulty, durationMin, questionMix, resumeId, sections, questions }
    // 环节进行状态
    currentSection: 'voice', // voice / coding / whiteboard
    // 语音问答
    voiceChat: [], // { role: 'interviewer'|'candidate', text, meta }（仅用于聊天区展示）
    // 按题分组的作答记录（评分依据）：[{ qIndex, sectionType, turns: [{speaker,content}], coding, explanation }]
    qaGroups: [],
    // 编程
    codingResults: [], // 每题 judge 结果
    // 白板
    whiteboard: { nodes: [], edges: [] },
    // 报告
    report: null,
    startedAt: null,
  }),

  getters: {
    questionsBySection: (s) => {
      const map = { voice: [], coding: [], whiteboard: [] }
      for (const q of s.session?.questions || []) map[q.section_type]?.push(q)
      return map
    },
    codingPassRate: (s) => {
      if (!s.codingResults.length) return 0
      const total = s.codingResults.reduce((a, r) => a + (r.total || 1), 0)
      const passed = s.codingResults.reduce((a, r) => a + (r.passed || 0), 0)
      return total ? passed / total : 0
    },
  },

  actions: {
    /** 将会话状态持久化到 sessionStorage，防止页面刷新丢失 */
    _persist() {
      try {
        sessionStorage.setItem('interview_state', JSON.stringify({
          session: this.session,
          currentSection: this.currentSection,
          voiceChat: this.voiceChat,
          qaGroups: this.qaGroups,
          codingResults: this.codingResults,
          whiteboard: this.whiteboard,
          startedAt: this.startedAt,
        }))
      } catch { /* 忽略存储异常 */ }
    },

    /** 从 sessionStorage 恢复会话状态 */
    _restore() {
      try {
        const raw = sessionStorage.getItem('interview_state')
        if (!raw) return
        const data = JSON.parse(raw)
        if (data.session) {
          this.session = data.session
          this.currentSection = data.currentSection || 'voice'
          this.voiceChat = data.voiceChat || []
          this.qaGroups = data.qaGroups || []
          this.codingResults = data.codingResults || []
          this.whiteboard = data.whiteboard || { nodes: [], edges: [] }
          this.startedAt = data.startedAt || null
        }
      } catch { /* 忽略恢复异常 */ }
    },

    /** 清除持久化状态 */
    _clearPersist() {
      try { sessionStorage.removeItem('interview_state') } catch { /* 忽略 */ }
    },


    /** 配置页确认后创建会话 */
    async createSession(config) {
      const userStore = useUserStore()
      this.reset()
      this.startedAt = Date.now()
      const resume = config.resume || null
      if (userStore.isLogin) {
        const detail = await api.post('/sessions', {
          position_id: config.positionId,
          difficulty: config.difficulty,
          duration_min: config.durationMin,
          question_mix: config.questionMix,
          resume_id: resume?.id || null,
        })
        this.session = {
          id: detail.id,
          isGuest: false,
          position: detail.position,
          difficulty: detail.difficulty,
          durationMin: detail.duration_min,
          questionMix: detail.question_mix,
          sections: detail.sections,
          questions: detail.questions,
        }
        await api.post(`/sessions/${detail.id}/start`)
      } else {
        // 游客模式：公开接口出题，不落库
        const posResp = await api.get('/positions')
        const pos = posResp.find((p) => p.id === config.positionId)
        const params = {
          position_code: pos?.code || 'backend',
          difficulty: config.difficulty,
          voice: config.questionMix.voice,
          coding: config.questionMix.coding,
          whiteboard: config.questionMix.whiteboard,
        }
        // 游客上传了简历，把技术栈标签传给后端用于优先推荐相关题目
        if (resume?.tech_tags?.length) {
          params.tags = resume.tech_tags.join(',')
        }
        const qs = await api.get('/questions/public', { params })
        const questions = []
        let seq = 0
        for (const sec of ['voice', 'coding', 'whiteboard']) {
          for (const q of qs[sec] || []) {
            seq += 1
            questions.push({ id: null, section_type: sec, sequence_no: seq, snapshot: q, source: 'builtin' })
          }
        }
        this.session = {
          id: `guest_${Date.now()}`,
          isGuest: true,
          position: pos ? { id: pos.id, name: pos.name } : null,
          difficulty: config.difficulty,
          durationMin: config.durationMin,
          questionMix: config.questionMix,
          resumeId: null,
          resumeSummary: resume?.summary || '',
          resumeTags: resume?.tech_tags || [],
          sections: ['voice', 'coding', 'whiteboard']
            .filter((t) => (config.questionMix[t] || 0) > 0)
            .map((t, i) => ({ id: null, section_type: t, sequence_no: i + 1, status: 'pending' })),
          questions,
        }
      }
      this._persist()
      return this.session
    },

    /** 找到/创建某道题的分组记录（评分时按题组装，杜绝多轮回答错位） */
    ensureGroup(question) {
      const qs = this.session?.questions
      if (!question || !qs) return null
      const idx = qs.indexOf(question)
      if (idx < 0) return null
      let g = this.qaGroups.find((x) => x.qIndex === idx)
      if (!g) {
        g = { qIndex: idx, sectionType: question.section_type, turns: [], coding: null, explanation: '' }
        this.qaGroups.push(g)
      }
      return g
    },

    /** 记录一条对话轮次 */
    recordTurn(question, speaker, content) {
      if (!content) return
      const g = this.ensureGroup(question)
      g?.turns.push({ speaker, content })
    },

    /** 跳过本题：记录占位回答，评分时按未作答处理 */
    recordSkip(question) {
      const g = this.ensureGroup(question)
      g?.turns.push({ speaker: 'candidate', content: '（本题跳过，未作答）' })
    },

    /** 记录口头讲解/思路说明（编程讲解、白板讲解） */
    recordExplanation(question, text) {
      const t = (text || '').trim()
      if (!t) return
      const g = this.ensureGroup(question)
      if (g) {
        g.explanation = t
        g.turns.push({ speaker: 'candidate', content: t })
      }
    },

    /** 语音问答：发送候选人回答，返回 AI 回复 */
    async sendAnswer(question, content, followupNo) {
      const g = this.ensureGroup(question)
      g?.turns.push({ speaker: 'candidate', content })
      let reply
      if (this.session.isGuest) {
        reply = await api.post('/interview/mock-reply', {
          question: question.snapshot, answer: content, followup_no: followupNo,
        })
      } else {
        const sec = this.session.sections.find((s) => s.section_type === 'voice')
        reply = await api.post(`/sessions/${this.session.id}/dialogue`, {
          content, question_id: question.id, section_id: sec?.id || null,
          followup_no: followupNo,
        })
      }
      // 把 AI 的追问/点评也记入本题轮次，作为评分上下文
      if (reply?.reply) g?.turns.push({ speaker: 'interviewer', content: reply.reply })
      return reply // { reply, is_followup }
    },

    /** 编程：提交代码判题 */
    async submitCode(question, language, code) {
      const g = this.ensureGroup(question)
      let result
      if (this.session.isGuest) {
        result = await api.post('/interview/run-code', {
          question: question.snapshot, language, code,
        })
      } else {
        const sec = this.session.sections.find((s) => s.section_type === 'coding')
        result = await api.post(`/sessions/${this.session.id}/coding/submit`, {
          section_id: sec?.id, question_id: question.id, language, code,
        })
      }
      this.codingResults.push(result)
      if (g) {
        g.coding = {
          language,
          code,
          passed: result.passed,
          total: result.total,
          output: result.output || '',
          run_status: result.run_status || '',
        }
      }
      return result
    },

    /** 白板快照自动保存 */
    async saveWhiteboard(content) {
      this.whiteboard = content
      if (!this.session.isGuest) {
        const sec = this.session.sections.find((s) => s.section_type === 'whiteboard')
        if (sec?.id) {
          await api.post(`/sessions/${this.session.id}/whiteboard/snapshot`, {
            section_id: sec.id, content,
          }).catch(() => {})
        }
      }
    },

    /** 结束面试，生成评分报告 */
    async finish() {
      const allQuestions = this.session.questions.map((q) => q.snapshot)
      // 按题组装评分数据：每题携带完整多轮对话 / 代码 / 白板，杜绝平铺错位
      const qa_groups = this.session.questions.map((q, idx) => {
        const g = this.qaGroups.find((x) => x.qIndex === idx)
        const base = { no: idx + 1, section_type: q.section_type }
        if (q.section_type === 'voice') {
          base.turns = g?.turns || []
        } else if (q.section_type === 'coding') {
          base.turns = g?.turns || []
          base.coding = g?.coding || { language: 'python', code: '', passed: 0, total: 1, output: '' }
        } else {
          base.turns = g?.turns || []
          base.whiteboard = {
            nodes: this.whiteboard.nodes.map((n) => n.label),
            edges: this.whiteboard.edges.length,
            explanation: g?.explanation || '',
          }
        }
        return base
      })
      const common = {
        qa_groups,
        coding_pass_rate: this.codingPassRate,
        whiteboard_elements: this.whiteboard.nodes.length,
      }
      if (this.session.isGuest) {
        const r = await api.post('/interview/evaluate', {
          questions: allQuestions,
          ...common,
        })
        // 包装成与登录报告一致的结构，供报告页展示
        this.report = {
          session: {
            id: this.session.id,
            status: 'completed',
            position: this.session.position,
            difficulty: this.session.difficulty,
            ended_at: new Date().toLocaleString('zh-CN'),
            sections: this.session.sections,
            questions: this.session.questions,
          },
          evaluation: { total_score: r.total_score || 0, overall_comment: r.overall_comment || '' },
          dimensions: r.dimensions || [],
          question_evaluations: r.question_evaluations || [],
          is_member: false,
        }
        this.saveGuestHistory()
      } else {
        this.report = await api.post(`/sessions/${this.session.id}/finish`, common)
      }
      return this.report
    },

    /** 游客历史存 localStorage */
    saveGuestHistory() {
      const list = JSON.parse(localStorage.getItem('guestHistory') || '[]')
      list.unshift({
        id: this.session.id,
        date: new Date().toLocaleString('zh-CN'),
        position: this.session.position?.name || '-',
        difficulty: this.session.difficulty,
        score: this.report?.evaluation?.total_score ?? this.report?.total_score ?? 0,
        comment: this.report?.evaluation?.overall_comment ?? this.report?.overall_comment ?? '',
      })
      localStorage.setItem('guestHistory', JSON.stringify(list.slice(0, 50)))
    },

    /** 登录用户从历史记录加载报告 */
    async loadServerReport(sessionId) {
      this.report = await api.get(`/sessions/${sessionId}/report`)
      return this.report
    },

    reset() {
      this.session = null
      this.currentSection = 'voice'
      this.voiceChat = []
      this.qaGroups = []
      this.codingResults = []
      this.whiteboard = { nodes: [], edges: [] }
      this.report = null
      this.startedAt = null
      this._clearPersist()
    },
  },
})
