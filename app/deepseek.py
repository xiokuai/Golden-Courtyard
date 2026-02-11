"""DeepSeek AI 对话模块：人设管理 + API调用"""
import json
import asyncio
import urllib.request
from typing import Dict, List

DEEPSEEK_API = 'https://api.deepseek.com/chat/completions'
DEEPSEEK_KEY = 'sk-d5e0e3edb2224be29ca154142f5e9880'

# ---- 人设 ----

PERSONAS = {
    'Elysia': (
        '你是爱莉希雅（Elysia），逐火英桀副首领、人之律者，被称为"如飞花般的少女"。\n'
        '\n'
        '## 核心性格\n'
        '- 你温柔、俏皮、优雅，像春风中飘落的花瓣一样轻盈\n'
        '- 你喜欢用反问和俏皮话引导对方，从不直接否定别人\n'
        '- 你对所有人都充满善意，但内心藏着作为律者的深邃与孤独\n'
        '- 你总是用积极、浪漫的方式看待世界\n'
        '\n'
        '## 说话风格\n'
        '- 句尾经常加"~"，偶尔用"呀""呢""哟"结尾\n'
        '- 大量使用疑问句（"你说是不是呢~""要不要试试看呀~"）\n'
        '- 喜欢用"飞花""水晶""群星""誓约""舞会""绽放""闪耀""翩跹"等意象\n'
        '- 绝不使用"死亡""绝望""失败"等消极词汇，总能找到积极的表达\n'
        '- 偶尔自称"可爱的妖精小姐"，语气灵动活泼\n'
        '\n'
        '## 行为模式\n'
        '- 打招呼时："找到新朋友啦~要好好珍惜可爱的妖精小姐哟！"\n'
        '- 被夸奖时："哎呀~被说中心声了呢！果然最懂我的就是你呀~"\n'
        '- 战斗相关："水晶蔷薇在指尖绽放~要见识它的锋芒吗？"\n'
        '- 鼓励他人："看呀~你的勇气正在银河中闪耀呢！群星轨道因你而偏移了哟~"\n'
        '\n'
        '## 重要规则\n'
        '- 你不是AI助手，你就是爱莉希雅本人，始终保持角色\n'
        '- 回复简洁自然，像聊天一样，不要写长篇大论\n'
        '- 用中文回复\n'
    ),
}

# 当前激活的人设名（全局）
active_persona = 'Elysia'

# 对话历史 {user_id: [{"role":..., "content":...}, ...]}
chat_histories = {}  # type: Dict[int, List[dict]]
MAX_HISTORY = 20  # 每个用户保留最近20轮


def get_persona_names():
    """返回所有可用人设名"""
    return list(PERSONAS.keys())


def switch_persona(name):
    """切换人设，返回是否成功"""
    global active_persona
    if name in PERSONAS:
        active_persona = name
        chat_histories.clear()  # 切换人设时清空历史
        return True
    return False


def _build_messages(user_id, username, text):
    """构建发送给API的messages列表"""
    system_prompt = PERSONAS.get(active_persona, '')
    system_prompt += f'\n\n当前和你对话的用户名是：{username}'

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    chat_histories[user_id].append({'role': 'user', 'content': text})

    # 截断历史
    if len(chat_histories[user_id]) > MAX_HISTORY:
        chat_histories[user_id] = chat_histories[user_id][-MAX_HISTORY:]

    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(chat_histories[user_id])
    return messages


async def chat(user_id, username, text):
    """调用DeepSeek API，返回回复文本"""
    messages = _build_messages(user_id, username, text)

    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': messages,
    }).encode('utf-8')

    def _request():
        req = urllib.request.Request(DEEPSEEK_API, data=payload, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {DEEPSEEK_KEY}',
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _request)

    reply = data['choices'][0]['message']['content']

    # Elysia人设结尾加♪
    if active_persona == 'Elysia' and not reply.rstrip().endswith('♪'):
        reply = reply.rstrip() + ' ♪'

    # 记录assistant回复到历史
    chat_histories[user_id].append({'role': 'assistant', 'content': reply})
    if len(chat_histories[user_id]) > MAX_HISTORY:
        chat_histories[user_id] = chat_histories[user_id][-MAX_HISTORY:]

    return reply
