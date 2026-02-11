"""B站视频解析：检测BV/AV号和链接，调用API，格式化Markdown"""
import re
import json
import asyncio
import os
import uuid
import urllib.request
import urllib.parse
from typing import Optional

# 匹配 bilibili 完整链接、b23短链、BV号、AV号
BILIBILI_PATTERN = re.compile(
    r'(https?://(?:www\.)?bilibili\.com/video/[A-Za-z0-9]+[^\s]*'
    r'|https?://b23\.tv/[A-Za-z0-9]+[^\s]*'
    r'|BV[a-zA-Z0-9]{10,}'
    r'|[Aa][Vv]\d+)',
)

API_URL = 'https://api.mir6.com/api/bzjiexi'

ERROR_MESSAGES = {
    -1: '解析失败：未提交url参数',
    201: '解析失败：视频解析失败',
    202: '解析失败：访问接口超过QPS限制（15次/秒），请稍后再试',
}


def extract_bilibili_id(text: str) -> Optional[str]:
    """从文本中提取第一个B站视频标识"""
    m = BILIBILI_PATTERN.search(text)
    return m.group(0) if m else None


def complete_url(identifier: str) -> str:
    """将BV/AV号补全为完整链接，已是完整链接则原样返回"""
    if identifier.startswith('http'):
        return identifier
    # BV号或AV号 -> 补全
    return f'https://www.bilibili.com/video/{identifier}'


async def fetch_video_info(identifier: str) -> dict:
    """调用API获取视频信息，返回原始JSON dict"""
    url = complete_url(identifier)
    api = f'{API_URL}?{urllib.parse.urlencode({"url": url, "type": "json"})}'

    def _request():
        req = urllib.request.Request(api, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _request)


def format_response(data: dict) -> str:
    """根据API返回的code格式化为Markdown或错误信息"""
    code = data.get('code')

    if code != 200:
        return ERROR_MESSAGES.get(code, f'解析失败：未知错误（code={code}）')

    title = data.get('title', '未知标题')
    imgurl = data.get('imgurl', '')
    video = data.get('data', [{}])[0] if data.get('data') else {}
    duration = video.get('durationFormat', '未知')
    video_url = video.get('video_url', '')
    up_name = data.get('user', {}).get('name', '未知UP主')

    lines = [
        f'**{title}**',
        f'![封面]({imgurl})' if imgurl else '',
        f'时长：{duration}',
        f'链接：{video_url}' if video_url else '',
        f'UP主：{up_name}',
    ]
    return '\n\n'.join(line for line in lines if line)


RANDOM_IMG_API = 'https://api.yppp.net/api.php'


async def fetch_random_image() -> str:
    """请求随机图片API，跟踪重定向获取最终图片URL，返回Markdown"""
    def _request():
        req = urllib.request.Request(RANDOM_IMG_API, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.url

    loop = asyncio.get_event_loop()
    img_url = await loop.run_in_executor(None, _request)
    return f'![随机图片]({img_url})'


async def download_avatar(url):
    """下载图片并保存到avatars目录，返回相对路径"""
    def _download():
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        resp = urllib.request.urlopen(req, timeout=10)
        content_type = resp.headers.get('Content-Type', '')
        if 'png' in content_type:
            ext = '.png'
        elif 'gif' in content_type:
            ext = '.gif'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            ext = '.jpg'
        filename = uuid.uuid4().hex[:12] + ext
        rel_path = os.path.join('avatars', filename)
        from django.conf import settings
        full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(resp.read())
        return rel_path

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download)
