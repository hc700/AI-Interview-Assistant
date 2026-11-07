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

    <!-- Hero -->
    <section style="background:linear-gradient(180deg,#F4F7FF,#fff);padding:72px 40px;">
      <div style="max-width:1120px;margin:0 auto;display:flex;gap:56px;align-items:center;flex-wrap:wrap;">
        <div style="flex:1;min-width:340px;">
          <span style="background:#EBEFFF;color:#3B5BFF;border-radius:999px;padding:6px 14px;font-size:13px;">🎯 技术岗求职者专属 · 免登录即可体验</span>
          <h1 style="font-size:44px;line-height:1.25;margin:22px 0 16px;">语音 · 编程 · 白板<br/>还原一场真实的技术面试</h1>
          <p style="color:var(--t2);font-size:16px;line-height:1.8;max-width:520px;">
            AI 面试官模拟真实面试节奏与压力：语音对话深挖项目、在线编程限时解题、白板画图讲系统设计。面试结束即刻评分，帮你在 Offer 前把每道题练熟。
          </p>
          <div style="display:flex;gap:14px;margin-top:28px;">
            <a-button type="primary" size="large" @click="$router.push('/config')">免费开始模拟面试</a-button>
            <a-button size="large" @click="$router.push('/pricing')">查看会员权益</a-button>
          </div>
          <p style="color:var(--t3);font-size:13px;margin-top:16px;">免注册 · 每月 3 场免费额度 · 无需安装任何插件</p>
        </div>
        <div style="flex:1;min-width:340px;background:#fff;border:1px solid var(--line2);border-radius:16px;padding:22px;box-shadow:0 8px 30px rgba(59,91,255,.08);">
          <div style="display:flex;justify-content:space-between;font-size:13px;color:var(--t3);">
            <b style="color:var(--t1);">AI 面试官 · 语音问答房间</b>
            <span style="color:var(--red);">● REC 00:24</span>
          </div>
          <div style="background:#F7F8FA;border-radius:10px;padding:14px;margin-top:14px;">
            <span style="background:#FFF1E8;color:#FF7A45;font-size:11px;border-radius:4px;padding:2px 8px;">正在提问 · 八股</span>
            <p style="font-weight:600;margin:10px 0 6px;">请讲讲 TCP 三次握手的过程，为什么不是两次握手？</p>
            <p style="color:var(--t3);font-size:12px;margin:0;">语音已播放 0:12 · 中等难度 · 追问就绪</p>
          </div>
          <div style="display:flex;align-items:flex-end;gap:3px;height:36px;margin:16px 0;color:#3B5BFF;">
            <i v-for="(h,i) in [12,26,18,32,14,28,20,34,16,24,30,12]" :key="i"
               :style="{ width:'6px',height:h+'px',background:'#3B5BFF',borderRadius:'3px',opacity:.7,animation:`wave 1s ${i*0.08}s infinite ease-in-out alternate` }" />
          </div>
          <div style="background:#EBEFFF;border-radius:10px;padding:14px;font-size:13px;color:var(--t2);line-height:1.7;">
            "三次握手是为了确认双方的发送与接收能力。第一次客户端发 SYN……第二次服务端回 SYN+ACK 后……"
          </div>
          <div style="display:flex;align-items:center;gap:8px;margin-top:14px;color:var(--t3);font-size:12px;">
            <a-spin size="small" /> AI 正在分析你的回答 · 准备追问
          </div>
        </div>
      </div>
    </section>

    <!-- 三种交互 -->
    <section style="padding:64px 40px;background:#fff;">
      <div style="text-align:center;margin-bottom:40px;">
        <h2 style="font-size:28px;margin:0 0 10px;">三种实战交互，覆盖技术面试全题型</h2>
        <p style="color:var(--t3);margin:0;">从口述到写码再到画图，AI 面试官全程陪伴式提问与点评</p>
      </div>
      <div style="max-width:1120px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;">
        <a-card v-for="f in features" :key="f.title" :bordered="false" style="border-radius:14px;box-shadow:0 2px 10px rgba(29,33,41,.05);">
          <div style="font-size:32px;">{{ f.icon }}</div>
          <h3 style="margin:14px 0 8px;">{{ f.title }}</h3>
          <p style="color:var(--t2);line-height:1.8;margin:0;">{{ f.desc }}</p>
        </a-card>
      </div>
    </section>

    <!-- 四步流程 -->
    <section style="padding:64px 40px;background:var(--bg);">
      <div style="text-align:center;margin-bottom:40px;">
        <h2 style="font-size:28px;margin:0 0 10px;">四步完成一场高质量模拟面试</h2>
        <p style="color:var(--t3);margin:0;">完整流程与真实面试一致，随时开始、立即得到反馈</p>
      </div>
      <div style="max-width:1120px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px;">
        <a-card v-for="(s,i) in steps" :key="i" :bordered="false" style="border-radius:14px;">
          <div style="font-size:26px;font-weight:800;color:#D6E4FF;">0{{ i+1 }}</div>
          <h4 style="margin:10px 0 8px;">{{ s.title }}</h4>
          <p style="color:var(--t2);line-height:1.7;margin:0;font-size:13px;">{{ s.desc }}</p>
        </a-card>
      </div>
    </section>

    <!-- 免费vs会员 -->
    <section style="padding:64px 40px;">
      <div style="max-width:880px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:32px;">
          <h2 style="font-size:28px;margin:0 0 10px;">免费版 vs 会员版</h2>
          <p style="color:var(--t3);margin:0;">先免费练起来，进阶后再解锁完整成长路径</p>
        </div>
        <a-table :columns="cmpCols" :data-source="cmpData" :pagination="false" style="border-radius:12px;overflow:hidden;" />
        <div style="text-align:center;margin-top:28px;">
          <a-button type="primary" size="large" @click="$router.push('/config')">立即开始第一场模拟面试</a-button>
        </div>
      </div>
    </section>

    <footer class="site-footer">
      <div>
        <div class="logo" style="color:#fff;">
          <span class="logo-mark"><svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" fill="#fff"/></svg></span>
          <span>AI 模拟面试助手</span>
        </div>
        <p class="f-slogan">用 AI 还原真实面试，把每一场练习都变成 Offer 前的底气。</p>
      </div>
      <div>
        <div class="f-links">
          <span @click="$router.push('/')">首页</span>
          <span @click="$router.push('/config')">开始面试</span>
          <span @click="$router.push('/pricing')">会员定价</span>
          <span @click="$router.push('/profile')">个人中心</span>
        </div>
        <p class="f-note">© 2026 AI 模拟面试助手 · 演示环境</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

const features = [
  { icon: '🎤', title: '语音问答', desc: '模拟真实口试节奏，AI 针对你的回答即时追问、深挖细节，覆盖八股、项目经历与系统设计论述题，练表达、练临场。' },
  { icon: '💻', title: '在线编程', desc: '内置在线代码编辑器与测试用例，算法题限时完成、一键运行，还原手撕代码的真实紧张感，提交后自动判题。' },
  { icon: '📐', title: '白板系统设计', desc: '在点阵白板上拖拽架构图、边讲边画，AI 实时观察你的设计思路，针对缓存一致性、容灾扩容等问题层层追问。' },
]
const steps = [
  { title: '配置面试', desc: '选岗位、难度与时长，拖拽滑块定制题目构成，也可上传简历让 AI 针对性提问。' },
  { title: '语音问答', desc: 'AI 面试官开口提问，你语音作答，追问环环相扣，还原口试压力。' },
  { title: '编程 + 白板', desc: '在线手撕算法题，再于白板上画架构、讲设计，多维度考察硬实力。' },
  { title: '即时评分', desc: '面试结束立刻出总分与整体评语，会员可解锁五维报告与逐题复盘。' },
]
const cmpCols = [
  { title: '功能对比', dataIndex: 'name' },
  { title: '免费版', dataIndex: 'free' },
  { title: '会员版', dataIndex: 'pro' },
]
const cmpData = [
  { key: '1', name: '每月模拟场次', free: '3 场', pro: '不限次' },
  { key: '2', name: '面后反馈', free: '总分 + 短评语', pro: '五维报告 + 逐题复盘' },
  { key: '3', name: '语音 / 编程 / 白板', free: '全部开放', pro: '全部开放 + 更密追问' },
  { key: '4', name: '简历定制提问', free: '仅内置题库', pro: '上传简历 · 针对性提问' },
  { key: '5', name: '历史与成长曲线', free: '仅保留本场', pro: '长期保存 · 成长曲线' },
]
</script>

<style>
@keyframes wave { from { transform: scaleY(.5); } to { transform: scaleY(1.2); } }
</style>
