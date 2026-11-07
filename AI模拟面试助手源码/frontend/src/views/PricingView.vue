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

    <div style="max-width:1120px;margin:0 auto;padding:48px 24px;">
      <div style="text-align:center;margin-bottom:40px;">
        <h2 style="font-size:30px;margin:0 0 10px;">会员定价 · 为你的 Offer 投资</h2>
        <p style="color:var(--t3);margin:0;">三档随心选，解锁不限次模拟面试与完整成长反馈，随时可取消。</p>
      </div>

      <div class="plans-grid">
        <div v-for="p in plans" :key="p.id"
             class="plan-card" :class="{ featured: p.plan_code === 'quarterly' }"
             role="button" @click="buy(p)">
          <span v-if="p.plan_code === 'quarterly'" class="plan-tag">🔥 季付最划算 · 省 33%</span>
          <h3 class="plan-name">{{ p.name }}</h3>
          <div class="plan-price">
            <span class="price-now">¥{{ p.price }}</span>
            <span class="price-period">/ {{ periodLabel(p.period_type) }}</span>
            <span v-if="p.original_price" class="price-orig">¥{{ p.original_price }}</span>
          </div>
          <ul class="plan-features">
            <li v-for="(f, i) in featureList(p.description)" :key="i">{{ f }}</li>
          </ul>
          <a-button class="plan-btn" :type="p.plan_code === 'quarterly' ? 'primary' : 'default'" size="large" block
                    @click.stop="buy(p)">选择 {{ p.name }}</a-button>
        </div>
      </div>

      <a-card style="border-radius:14px;margin-top:40px;" :bordered="false">
        <h3 style="margin-top:0;">常见问题</h3>
        <a-collapse :bordered="false">
          <a-collapse-panel v-for="f in faqs" :key="f.q" :header="f.q">
            <p style="color:var(--t2);line-height:1.9;margin:0;">{{ f.a }}</p>
          </a-collapse-panel>
        </a-collapse>
      </a-card>

      <p style="color:var(--t3);font-size:12px;text-align:center;margin-top:24px;">
        * 请使用微信 / 支付宝扫码付款，付款成功后点击「我已完成支付」即可开通会员。
      </p>
    </div>

    <!-- 扫码收银台（个人收款码） -->
    <a-modal v-model:open="payOpen" title="收银台 · 扫码支付" :footer="null" width="420px">
      <div class="pay-box">
        <p class="pay-label">购买套餐</p>
        <p class="pay-plan">{{ payingPlan?.name }}</p>
        <p class="pay-amount">¥{{ payingPlan?.price }}</p>

        <a-radio-group v-model:value="payChannel" class="pay-tabs">
          <a-radio-button value="wechat">微信支付</a-radio-button>
          <a-radio-button value="alipay">支付宝</a-radio-button>
        </a-radio-group>

        <div class="qr-wrap" :class="payChannel">
          <img :src="QR_IMAGES[payChannel]" :alt="payChannel === 'wechat' ? '微信收款码' : '支付宝收款码'"
               class="pay-qr" />
        </div>

        <p class="pay-tip">
          请打开<strong>{{ payChannel === 'wechat' ? '微信' : '支付宝' }}</strong>「扫一扫」，
          向收款方 <strong>{{ PAYEE_NAMES[payChannel] }}</strong> 付款
          <strong class="pay-tip-amount">¥{{ payingPlan?.price }}</strong>
        </p>
        <p class="pay-tip-sub">付款前请核对收款方姓名；支付完成后点击下方按钮，系统将立即开通会员权益。</p>

        <a-button type="primary" size="large" block :loading="paying" @click="confirmPay">我已完成支付</a-button>
        <a-button type="text" block style="margin-top:6px;" @click="payOpen = false">取消</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import api, { toastError } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const plans = ref([])
const payOpen = ref(false)
const payingPlan = ref(null)
const payChannel = ref('wechat')
const paying = ref(false)

const periodLabel = (p) => ({ monthly: '月', quarterly: '季', yearly: '年' }[p] || p)

// 套餐说明是用「·」分隔的一句话，拆成权益清单展示，避免整段文字换行错乱
const featureList = (desc) => (desc ? desc.split('·').map((s) => s.trim()).filter(Boolean) : [])

// 个人收款码（放在 frontend/public/pay/ 下，Vite 会原样发布）
const QR_IMAGES = { wechat: '/pay/wechat.png', alipay: '/pay/alipay.jpg' }
// 收款方姓名（与收款码一致，用于付款前核对）
const PAYEE_NAMES = { wechat: '哈(*聪)', alipay: '麻格吉尔(*聪)' }

const faqs = [
  { q: 'Q1：免费额度什么时候刷新？', a: '自然月 1 日 0 点重置为 3 场。未使用的额度不结转，建议每周固定练 1 场保持手感。会员不限场次，不受刷新规则影响。' },
  { q: 'Q2：如何取消订阅？会扣费吗？', a: '进入「个人中心 → 会员与订阅」点击取消订阅即可，取消后当期权益保留至到期日，不会二次扣费。付款通过微信/支付宝个人收款码扫码完成，付款后点击「我已完成支付」即可即时开通。' },
  { q: 'Q3：上传的简历数据安全吗？', a: '简历仅用于生成定制面试问题，支持随时在个人中心删除；删除后系统立即清除相关数据，不用于任何其他用途。' },
]

async function buy(plan) {
  if (!userStore.isLogin) {
    message.info('请先登录后再购买会员')
    return router.push('/login')
  }
  payingPlan.value = plan
  payOpen.value = true
}

async function confirmPay() {
  if (!payingPlan.value) return
  paying.value = true
  try {
    const order = await api.post('/orders', { plan_id: payingPlan.value.id, pay_channel: payChannel.value })
    await api.post(`/orders/${order.order_id}/confirm-pay`)
    await userStore.refresh()
    message.success(`支付成功，${payingPlan.value.name}已开通 🎉`)
    payOpen.value = false
    router.push('/profile')
  } catch (e) {
    toastError(e)
  } finally { paying.value = false }
}

onMounted(async () => {
  try {
    plans.value = await api.get('/plans')
  } catch (e) {
    toastError(e)
  }
})
</script>

<style scoped>
.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  align-items: stretch;
}

.plan-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 28px;
  background: #fff;
  border: 2px solid var(--line);
  border-radius: 16px;
  cursor: pointer;
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.plan-card:hover {
  transform: translateY(-3px);
  border-color: #B7C4FF;
  box-shadow: 0 12px 32px rgba(59, 91, 255, .14);
}
.plan-card.featured {
  border-color: var(--primary);
  background: #F7F9FF;
}
.plan-card.featured:hover {
  border-color: var(--primary);
}

.plan-tag {
  position: absolute;
  top: -12px;
  left: 24px;
  padding: 2px 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, #FFB400, #FF7A45);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.plan-name {
  margin: 0 0 12px;
  font-size: 18px;
}

.plan-price {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.price-now {
  font-size: 38px;
  font-weight: 800;
  line-height: 1;
}
.price-period {
  color: var(--t3);
}
.price-orig {
  margin-left: 6px;
  color: #C0C6D1;
  font-size: 13px;
  text-decoration: line-through;
}

.plan-features {
  flex: 1;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--t2);
  font-size: 13px;
  line-height: 1.9;
}
.plan-features li {
  padding-left: 20px;
  position: relative;
}
.plan-features li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: var(--primary);
  font-weight: 700;
}

.plan-btn {
  margin-top: 22px;
}

/* 扫码收银台 */
.pay-box {
  text-align: center;
  padding: 4px 0;
}
.pay-label {
  margin: 0 0 2px;
  color: var(--t3);
  font-size: 13px;
}
.pay-plan {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
}
.pay-amount {
  margin: 0 0 16px;
  font-size: 34px;
  font-weight: 800;
  color: var(--primary);
  line-height: 1.1;
}
.pay-tabs {
  margin-bottom: 16px;
}
.qr-wrap {
  width: 250px;
  margin: 0 auto 14px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
}
.pay-qr {
  display: block;
  width: 100%;
  border-radius: 8px;
}
.pay-tip {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--t1);
  line-height: 1.7;
}
.pay-tip strong {
  color: var(--primary);
}
.pay-tip-amount {
  font-size: 16px;
}
.pay-tip-sub {
  margin: 0 0 18px;
  font-size: 12px;
  color: var(--t3);
  line-height: 1.7;
}
</style>
