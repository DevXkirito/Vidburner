import os
import time
import re
import asyncio
from config import Config
from pyrogram.types import InputMediaPhoto
from helper_func.progress_bar import safe_edit_message


# --- Utilities ---

def parse_progress(line):
    progress_pattern = re.compile(r'(frame|fps|size|time|bitrate|speed)\s*=\s*(\S+)')
    items = {key: value for key, value in progress_pattern.findall(line)}
    return items if items else None


async def readlines(stream):
    pattern = re.compile(br'[\r\n]+')
    data = bytearray()
    while not stream.at_eof():
        lines = pattern.split(data)
        data[:] = lines.pop(-1)
        for line in lines:
            yield line
        data.extend(await stream.read(1024))


async def read_stderr(start, msg, process):
    last_edit_time = 0
    async for line in readlines(process.stderr):
        line = line.decode('utf-8')
        progress = parse_progress(line)
        if progress:
            now = time.time()
            if now - last_edit_time >= 5:  # Throttle updates
                text = '📊 Muxing Progress\n'
                text += f"📦 Size: {progress['size']}\n"
                text += f"⏱️ Time: {progress['time']}\n"
                text += f"⚡ Speed: {progress['speed']}\n"
                try:
                    await msg.edit(text)
                    last_edit_time = now
                except:
                    pass


async def send_screenshots(client, chat_id, video_path):
    duration_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    proc = await asyncio.create_subprocess_exec(
        *duration_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    try:
        duration = float(stdout.decode().strip())
    except ValueError:
        duration = 0

    if duration == 0:
        return

    interval = duration // 6
    screenshot_paths = []

    for i in range(1, 6):
        ss_time = int(i * interval)
        output_path = f"{video_path}_ss{i}.jpg"
        cmd = [
            "ffmpeg", "-ss", str(ss_time),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            "-y", output_path
        ]
        await asyncio.create_subprocess_exec(*cmd)
        screenshot_paths.append(output_path)

    media_group = [InputMediaPhoto(media=path) for path in screenshot_paths]
    await client.send_media_group(chat_id, media=media_group)


# --- Mux Functions ---

async def softmux_vid(vid_filename, sub_filename, msg):
    start = time.time()
    vid = os.path.join(Config.DOWNLOAD_DIR, vid_filename)
    sub = os.path.join(Config.DOWNLOAD_DIR, sub_filename)
    out_file = '.'.join(vid_filename.split('.')[:-1])
    output = out_file + '1.mkv'
    out_location = os.path.join(Config.DOWNLOAD_DIR, output)
    sub_ext = sub_filename.split('.')[-1]

    command = [
        'ffmpeg', '-hide_banner',
        '-i', vid,
        '-i', sub,
        '-map', '1:0', '-map', '0',
        '-disposition:s:0', 'default',
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-c:s', sub_ext,
        '-y', out_location
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await asyncio.wait([
        read_stderr(start, msg, process),
        process.wait()
    ])

    if process.returncode == 0:
        await msg.edit('✅ Muxing Completed Successfully!\n\n⏱️ Time taken: {}s'.format(round(time.time() - start)))
        await send_screenshots(msg._client, msg.chat.id, out_location)
        return output
    else:
        await msg.edit("❌ Muxing Failed! Please check your files or format.")
        return False


async def softremove_vid(vid_filename, sub_filename, msg):
    start = time.time()
    vid = os.path.join(Config.DOWNLOAD_DIR, vid_filename)
    sub = os.path.join(Config.DOWNLOAD_DIR, sub_filename)
    out_file = '.'.join(vid_filename.split('.')[:-1])
    output = out_file + '1.mkv'
    out_location = os.path.join(Config.DOWNLOAD_DIR, output)
    sub_ext = sub_filename.split('.')[-1]

    command = [
        'ffmpeg', '-hide_banner',
        '-i', vid,
        '-i', sub,
        '-map', '0:v:0',
        '-map', '0:a?',
        '-map', '1:0',
        '-disposition:s:0', 'default',
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-c:s', sub_ext,
        '-y', out_location
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await asyncio.wait([
        read_stderr(start, msg, process),
        process.wait()
    ])

    if process.returncode == 0:
        await msg.edit('✅ Muxing Completed Successfully!\n\n⏱️ Time taken: {}s'.format(round(time.time() - start)))
        await send_screenshots(msg._client, msg.chat.id, out_location)
        return output
    else:
        await msg.edit("❌ Muxing Failed! Please check your files or format.")
        return False


async def hardmux_vid(vid_filename, sub_filename, msg):
    start = time.time()
    vid = os.path.join(Config.DOWNLOAD_DIR, vid_filename)
    sub = os.path.join(Config.DOWNLOAD_DIR, sub_filename)
    out_file = '.'.join(vid_filename.split('.')[:-1])
    output = out_file + '_muxed.mp4'
    out_location = os.path.join(Config.DOWNLOAD_DIR, output)

    # Font check
    font_path = os.path.join(os.getcwd(), "fonts", "HelveticaRounded-Bold.ttf")
    if not os.path.exists(font_path):
        await safe_edit_message(msg, "❌ Font not found! Place 'HelveticaRounded-Bold.ttf' in 'fonts' folder.")
        return False

    formatted_sub = "'{}'".format(sub.replace(":", "\\:")) if " " in sub else sub.replace(":", "\\:")

    command = [
        'ffmpeg', '-hide_banner',
        '-i', vid,
        '-vf', f"subtitles={formatted_sub}:force_style='FontName=HelveticaRounded-Bold,FontSize=20,MarginV=38'",
        '-c:v', 'libx265',
        '-crf', '23',
        '-preset', 'veryfast',
        '-r', '30',
        '-map', '0:v:0',
        '-map', '0:a:0?',
        '-y', out_location
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    await asyncio.wait([
        read_stderr(start, msg, process),
        process.wait()
    ])

    if process.returncode == 0:
        await msg.edit('✅ Muxing Completed Successfully!\n\n⏱️ Time taken: {}s'.format(round(time.time() - start)))
        await send_screenshots(msg._client, msg.chat.id, out_location)
        return output
    else:
        await msg.edit("❌ Muxing Failed! Please check your files or format.")
        return False
