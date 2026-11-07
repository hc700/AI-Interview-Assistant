"""端到端测试：覆盖 12 个核心业务接口。"""
import requests

B = 'http://localhost:8000/api'

# 1. 登录
r = requests.post(f'{B}/auth/login', json={'email': 'demo@interview.cn', 'password': '123456'}).json()
token = r['token']
H = {'Authorization': f'Bearer {token}'}
print('1 登录 OK:', r['user']['nickname'])

# 2. 岗位
positions = requests.get(f'{B}/positions').json()
print('2 岗位 OK:', [p['name'] for p in positions][:3], '...')

# 3. 总览（种子历史）
ov = requests.get(f'{B}/users/me/overview', headers=H).json()
print('3 总览 OK: 场次', ov['total_sessions'], '均分', ov['avg_score'], '曲线点', len(ov['trend']))

# 4. 创建面试会话
s = requests.post(f'{B}/sessions', headers=H, json={
    'position_id': positions[0]['id'], 'difficulty': 2, 'duration_min': 45,
    'question_mix': {'voice': 3, 'coding': 1, 'whiteboard': 1}}).json()
print('4 建会话 OK:', s['id'], 'sections', len(s['sections']), 'questions', len(s['questions']))

# 5. 开始
requests.post(f'{B}/sessions/{s["id"]}/start', headers=H)
print('5 开始 OK')

# 6. 语音问答（追问）
vq = [q for q in s['questions'] if q['section_type'] == 'voice']
d1 = requests.post(f'{B}/sessions/{s["id"]}/dialogue', headers=H, json={
    'content': '我负责过积分发放服务，峰值QPS约8万，用本地缓存加Redis，写操作走MQ削峰，消费端批量落库，整体稳定性达标。',
    'question_id': vq[0]['id'], 'followup_no': 0}).json()
print('6 问答 OK: 追问=', d1['is_followup'], '|', d1['reply'][:30])

# 7. 编程提交
cq = [q for q in s['questions'] if q['section_type'] == 'coding'][0]
sec = [x for x in s['sections'] if x['section_type'] == 'coding'][0]
cr = requests.post(f'{B}/sessions/{s["id"]}/coding/submit', headers=H, json={
    'section_id': sec['id'], 'question_id': cq['id'], 'language': 'python',
    'code': 'class Solution:\n    def solve(self, nums):\n        return nums[::-1]\n'}).json()
print('7 判题 OK:', cr['passed'], '/', cr['total'])

# 8. 白板快照
wbsec = [x for x in s['sections'] if x['section_type'] == 'whiteboard'][0]
requests.post(f'{B}/sessions/{s["id"]}/whiteboard/snapshot', headers=H,
              json={'section_id': wbsec['id'], 'content': {'nodes': [1, 2, 3], 'edges': []}})
print('8 白板 OK')

# 9. 结束评分
rep = requests.post(f'{B}/sessions/{s["id"]}/finish', headers=H, json={
    'answers': ['我负责过积分发放服务，峰值QPS约8万，采用缓存与MQ削峰方案，稳定性良好。'] * 4,
    'coding_pass_rate': 1.0, 'whiteboard_elements': 3}).json()
print('9 评分 OK: 总分', rep['evaluation']['total_score'], '| 会员', rep['is_member'])

# 10. 配额
q = requests.get(f'{B}/users/me/quota', headers=H).json()
print('10 配额 OK:', q)

# 11. 套餐 + 下单 + 扫码支付确认
plans = requests.get(f'{B}/plans').json()
order = requests.post(f'{B}/orders', headers=H, json={'plan_id': plans[1]['id']}).json()
pay = requests.post(f'{B}/orders/{order["order_id"]}/confirm-pay', headers=H).json()
print('11 支付 OK:', pay['subscription'])

# 12. 支付后再看报告（应解锁五维）
rep2 = requests.get(f'{B}/sessions/{s["id"]}/report', headers=H).json()
print('12 报告 OK: 会员=', rep2['is_member'], '五维', len(rep2['dimensions']),
      '逐题', len(rep2['question_evaluations']))

# 13. 游客公开接口
qs = requests.get(f'{B}/questions/public', params={'voice': 2, 'coding': 1, 'whiteboard': 1}).json()
print('13 游客出题 OK:', {k: len(v) for k, v in qs.items()})
mr = requests.post(f'{B}/interview/mock-reply', json={'question': qs['voice'][0], 'answer': '短答', 'followup_no': 0}).json()
print('14 游客追问 OK:', mr['reply'][:24])
ge = requests.post(f'{B}/interview/evaluate', json={'questions': qs['voice'], 'answers': ['详细回答' * 30], 'coding_pass_rate': 1, 'whiteboard_elements': 5}).json()
print('15 游客评分 OK:', ge['total_score'])

print('=== 全链路测试通过 ===')
