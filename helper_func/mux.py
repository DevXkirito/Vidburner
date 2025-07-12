import os
import re
import time
import random
import asyncio
from config import Config
from helper_func.progress_bar import safe_edit_message
from pyrogram.types import InputMediaPhoto


# ---------------------- Utilities ----------------------

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
            if now - last_edit_time >= 5:
                text = '📊 Muxing Progress\n'
                text += f"📦 Size: {progress['size']}\n"
                text += f"⏱️ Time: {progress['time']}\n"
                text += f"⚡ Speed: {progress['speed']}\n"
                try:
                    await msg.edit(text)
                    last_edit_time = now
                except:
                    pass


async def generate_screenshots(video_path, num_screenshots=5):
    """Generate multiple screenshots at 10s intervals."""
    screenshot_paths = []

    for i in range(num_screenshots):
        timestamp = i * 10
        screenshot_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_screenshot_{i+1}.jpg"
        screenshot_path = os.path.join(Config.DOWNLOAD_DIR, screenshot_filename)

        command = [
            'ffmpeg', '-hide_banner', '-ss', str(timestamp), '-i', video_path,
            '-frames:v', '1', '-q:v', '2', '-y', screenshot_path
        ]

        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0 and os.path.exists(screenshot_path):
            screenshot_paths.append(screenshot_path)
        else:
            print(f"⚠️ Screenshot {i+1} failed: {stderr.decode()}")

    return screenshot_paths


async def send_screenshots(msg, screenshots):
    """Send screenshots as individual photos."""
    if screenshots:
        await msg.reply_text("📸 **Screenshots Generated:**")
        for screenshot in screenshots:
            await msg.reply_photo(screenshot)


# ---------------------- Mux Functions ----------------------

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
        stderr=asyncio.subprocess.PIPE
    )

    await asyncio.wait([
        read_stderr(start, msg, process),
        process.wait()
    ])

    if process.returncode == 0:
        await msg.edit(f'✅ Muxing Completed Successfully!\n\n⏱️ Time taken: {round(time.time() - start)}s')
        screenshots = await generate_screenshots(out_location)
        await send_screenshots(msg, screenshots)
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
        stderr=asyncio.subprocess.PIPE
    )

    await asyncio.wait([
        read_stderr(start, msg, process),
        process.wait()
    ])

    if process.returncode == 0:
        await msg.edit(f'✅ Muxing Completed Successfully!\n\n⏱️ Time taken: {round(time.time() - start)}s')
        screenshots = await generate_screenshots(out_location)
        await send_screenshots(msg, screenshots)
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

    # Check font exists
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
        await msg.edit(f'✅ Muxing Completed Successfully!\n\n⏱️ Time taken: {round(time.time() - start)}s')
        screenshots = await generate_screenshots(out_location)
        await send_screenshots(msg, screenshots)
        return output
    else:
        await msg.edit("❌ Muxing Failed! Please check your files or format.")
        return False
