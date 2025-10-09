from pyrogram import Client, filters
from pyrogram.types import Message, ForceReply
from PIL import Image, ImageDraw, ImageFont
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import AshutoshGoswami24
from config import Config
import os
import time
import re
import traceback
import requests
import asyncio
import cv2
import numpy as np
from bot import app

# Configuration - Add your intro title video URL here
INTRO_TITLE_VIDEO_URL = os.environ.get("INTRO_TITLE_VIDEO", "https://envs.sh/your_intro_video.mp4")
JAI_BAJARANGABALI_CHANNEL = -1002987317144
JAI_BAJARANGABALI_THUMB_BASE = "https://envs.sh/zcf.jpg"

# Temporary storage for user states
autotrim_states = {}


def download_intro_template():
    """Download intro title template video"""
    try:
        template_path = "templates/intro_title.mp4"
        os.makedirs("templates", exist_ok=True)
        
        if not os.path.exists(template_path):
            print("Downloading intro template...")
            response = requests.get(INTRO_TITLE_VIDEO_URL, timeout=30)
            with open(template_path, 'wb') as f:
                f.write(response.content)
            print("✓ Intro template downloaded")
        
        return template_path
    except Exception as e:
        print(f"Error downloading intro template: {e}")
        return None


def extract_intro_frame(template_path):
    """Extract a frame from intro video for matching"""
    try:
        cap = cv2.VideoCapture(template_path)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Convert to grayscale for better matching
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return gray
        return None
    except Exception as e:
        print(f"Error extracting intro frame: {e}")
        return None


def find_intro_appearances(video_path, template_frame, progress_callback=None):
    """Find all appearances of intro title card in video"""
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        appearances = []
        frame_count = 0
        last_match_frame = -100
        
        # Check every 5th frame for performance
        skip_frames = 5
        threshold = 0.75  # Similarity threshold
        
        print(f"Analyzing video: {duration:.1f}s, {total_frames} frames, {fps:.1f} fps")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % skip_frames == 0:
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Resize to match template size
                if gray.shape != template_frame.shape:
                    gray = cv2.resize(gray, (template_frame.shape[1], template_frame.shape[0]))
                
                # Calculate similarity
                result = cv2.matchTemplate(gray, template_frame, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # If similarity is high and not too close to last match
                if max_val >= threshold and (frame_count - last_match_frame) > (fps * 3):
                    timestamp = frame_count / fps
                    appearances.append({
                        'frame': frame_count,
                        'timestamp': timestamp,
                        'similarity': max_val
                    })
                    last_match_frame = frame_count
                    print(f"✓ Found intro at {timestamp:.1f}s (similarity: {max_val:.2f})")
                
                # Progress callback
                if progress_callback and frame_count % (skip_frames * 50) == 0:
                    progress = (frame_count / total_frames) * 100
                    asyncio.create_task(progress_callback(progress))
            
            frame_count += 1
        
        cap.release()
        print(f"Total appearances found: {len(appearances)}")
        return appearances, duration, fps
    
    except Exception as e:
        print(f"Error finding intro appearances: {e}\n{traceback.format_exc()}")
        return [], 0, 0


def calculate_trim_segments(appearances, duration):
    """Calculate video segments to keep based on intro appearances"""
    if len(appearances) < 2:
        print("⚠️ Not enough intro appearances found")
        return [(0, duration)]
    
    segments = []
    
    # Keep from start to before 2nd appearance
    if len(appearances) >= 2:
        segments.append((0, appearances[1]['timestamp'] - 0.5))
    
    # Keep from after 3rd to before 4th appearance
    if len(appearances) >= 4:
        segments.append((appearances[2]['timestamp'] + 5.0, appearances[3]['timestamp'] - 0.5))
    
    # Keep from after 5th to before 6th appearance
    if len(appearances) >= 6:
        segments.append((appearances[4]['timestamp'] + 5.0, appearances[5]['timestamp'] - 0.5))
    
    # If only 4 appearances, keep from after 3rd to end
    elif len(appearances) == 4:
        segments.append((appearances[2]['timestamp'] + 5.0, duration))
    
    print(f"Calculated {len(segments)} segments to keep:")
    for i, (start, end) in enumerate(segments, 1):
        print(f"  Segment {i}: {start:.1f}s - {end:.1f}s ({end-start:.1f}s)")
    
    return segments


def trim_and_merge_video(video_path, segments, output_path, progress_callback=None):
    """Trim video into segments and merge them"""
    try:
        segment_files = []
        segments_dir = "downloads/segments"
        os.makedirs(segments_dir, exist_ok=True)
        
        # Create segment files
        for i, (start, end) in enumerate(segments, 1):
            segment_file = os.path.join(segments_dir, f"segment_{i}.mp4")
            
            # FFmpeg command to extract segment
            cmd = f'ffmpeg -i "{video_path}" -ss {start} -to {end} -c copy -avoid_negative_ts 1 "{segment_file}" -y'
            
            print(f"Extracting segment {i}...")
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if os.path.exists(segment_file):
                segment_files.append(segment_file)
                if progress_callback:
                    progress = (i / len(segments)) * 50
                    await progress_callback(progress)
        
        if not segment_files:
            return False
        
        # Create concat file for ffmpeg
        concat_file = os.path.join(segments_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            for seg_file in segment_files:
                f.write(f"file '{os.path.abspath(seg_file)}'\n")
        
        # Merge segments
        print("Merging segments...")
        merge_cmd = f'ffmpeg -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}" -y'
        
        process = await asyncio.create_subprocess_shell(
            merge_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        # Cleanup segment files
        for seg_file in segment_files:
            try:
                os.remove(seg_file)
            except:
                pass
        try:
            os.remove(concat_file)
        except:
            pass
        
        return os.path.exists(output_path)
    
    except Exception as e:
        print(f"Error trimming video: {e}\n{traceback.format_exc()}")
        return False


def generate_thumbnail_with_episode(base_thumb_url, episode_number, output_path):
    """Generate thumbnail with episode number overlay"""
    try:
        # Download base thumbnail
        response = requests.get(base_thumb_url, timeout=10)
        thumb_path = "temp_thumb.jpg"
        with open(thumb_path, 'wb') as f:
            f.write(response.content)
        
        # Open image
        img = Image.open(thumb_path)
        draw = ImageDraw.Draw(img)
        
        # Calculate font size based on image dimensions
        font_size = int(img.width * 0.08)
        
        try:
            # Try to use a bold font
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Episode text
        ep_text = f"Ep:{episode_number}"
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), ep_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position in top-left corner
        x = int(img.width * 0.05)
        y = int(img.height * 0.05)
        
        # Draw black background for text
        padding = 10
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, 180)
        )
        
        # Draw episode text in yellow/gold color
        draw.text((x, y), ep_text, fill=(255, 215, 0), font=font)
        
        # Resize to thumbnail size
        img = img.resize((320, 320), Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", quality=90)
        
        # Cleanup
        os.remove(thumb_path)
        
        return True
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return False


@Client.on_message(filters.private & filters.command("autotrim"))
async def autotrim_command(client, message: Message):
    """Handle autotrim command"""
    user_id = message.from_user.id
    
    try:
        # Extract video link
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            return await message.reply_text(
                "**Usage:** `/autotrim <video_link>`\n\n"
                "**Example:**\n"
                "`/autotrim https://example.com/jai-bajarangabali-ep11.mp4`\n\n"
                "This will automatically trim the video and remove all intro title cards except the first one."
            )
        
        video_url = parts[1].strip()
        
        # Validate URL
        if not video_url.startswith('http'):
            return await message.reply_text("❌ Invalid URL! Please provide a valid video link.")
        
        # Start processing
        status_msg = await message.reply_text(
            "🔧 **Auto-Trim Started!**\n\n"
            "⏳ Step 1/6: Preparing intro template..."
        )
        
        # Download intro template
        template_path = download_intro_template()
        if not template_path:
            return await status_msg.edit("❌ Failed to download intro template!")
        
        # Extract intro frame
        await status_msg.edit(
            "🔧 **Auto-Trim Started!**\n\n"
            "⏳ Step 2/6: Extracting intro frame..."
        )
        
        template_frame = extract_intro_frame(template_path)
        if template_frame is None:
            return await status_msg.edit("❌ Failed to extract intro frame!")
        
        # Download video
        await status_msg.edit(
            "🔧 **Auto-Trim Started!**\n\n"
            "📥 Step 3/6: Downloading video..."
        )
        
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        video_filename = f"autotrim_{int(time.time())}.mp4"
        video_path = os.path.join(downloads_dir, video_filename)
        
        # Download video using requests
        try:
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0 and downloaded % (1024 * 1024) == 0:  # Update every MB
                            progress = (downloaded / total_size) * 100
                            try:
                                await status_msg.edit(
                                    f"🔧 **Auto-Trim Started!**\n\n"
                                    f"📥 Step 3/6: Downloading video...\n"
                                    f"Progress: {progress:.1f}%"
                                )
                            except:
                                pass
        except Exception as e:
            return await status_msg.edit(f"❌ Download failed: {str(e)}")
        
        if not os.path.exists(video_path):
            return await status_msg.edit("❌ Video download failed!")
        
        # Find intro appearances
        await status_msg.edit(
            "🔧 **Auto-Trim Started!**\n\n"
            "🔍 Step 4/6: Analyzing video for intro cards..."
        )
        
        async def analysis_progress(progress):
            try:
                await status_msg.edit(
                    f"🔧 **Auto-Trim Started!**\n\n"
                    f"🔍 Step 4/6: Analyzing video...\n"
                    f"Progress: {progress:.1f}%"
                )
            except:
                pass
        
        appearances, duration, fps = find_intro_appearances(video_path, template_frame, analysis_progress)
        
        if len(appearances) < 2:
            os.remove(video_path)
            return await status_msg.edit(
                f"⚠️ **Insufficient intro cards found!**\n\n"
                f"Found: {len(appearances)} appearances\n"
                f"Required: At least 2\n\n"
                f"Please check if this is the correct video."
            )
        
        await status_msg.edit(
            f"✅ **Analysis Complete!**\n\n"
            f"📊 Found {len(appearances)} intro card appearances:\n" +
            "\n".join([f"• {i+1}. At {app['timestamp']:.1f}s" for i, app in enumerate(appearances[:6])]) +
            f"\n\n✂️ Step 5/6: Trimming and merging..."
        )
        
        # Calculate trim segments
        segments = calculate_trim_segments(appearances, duration)
        
        # Trim and merge
        output_filename = f"trimmed_{int(time.time())}.mp4"
        output_path = os.path.join(downloads_dir, output_filename)
        
        async def trim_progress(progress):
            try:
                await status_msg.edit(
                    f"✂️ **Trimming Video...**\n\n"
                    f"Progress: {progress:.1f}%"
                )
            except:
                pass
        
        success = await trim_and_merge_video(video_path, segments, output_path, trim_progress)
        
        if not success or not os.path.exists(output_path):
            os.remove(video_path)
            return await status_msg.edit("❌ Video trimming failed!")
        
        # Ask for filename
        await status_msg.edit(
            "✅ **Trimming Complete!**\n\n"
            "📝 Step 6/6: Please send the new filename\n\n"
            "**Example:** `Jai Bajarangabali Episode 11.mp4`"
        )
        
        # Store state for next message
        autotrim_states[user_id] = {
            'video_path': output_path,
            'original_path': video_path,
            'status_msg': status_msg,
            'appearances': appearances
        }
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Autotrim error: {e}\n{error_trace}")
        await message.reply_text(f"❌ **Error:** `{str(e)}`")


@Client.on_message(filters.private & filters.text)
async def handle_filename_response(client, message: Message):
    """Handle filename response for autotrim"""
    user_id = message.from_user.id
    
    # Check if user is in autotrim state
    if user_id not in autotrim_states:
        return
    
    state = autotrim_states[user_id]
    video_path = state['video_path']
    original_path = state['original_path']
    status_msg = state['status_msg']
    appearances = state['appearances']
    
    try:
        new_filename = message.text.strip()
        
        # Extract episode number from filename
        episode_match = re.search(r'(?:Episode|Ep|E)\s*(\d+)', new_filename, re.IGNORECASE)
        episode_number = episode_match.group(1) if episode_match else "1"
        
        # Generate thumbnail
        await status_msg.edit("🎨 Generating custom thumbnail...")
        
        thumb_path = os.path.join("downloads", f"thumb_{int(time.time())}.jpg")
        thumb_success = generate_thumbnail_with_episode(
            JAI_BAJARANGABALI_THUMB_BASE,
            episode_number,
            thumb_path
        )
        
        # Get file info
        file_size = os.path.getsize(video_path)
        
        # Get video metadata
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
        except:
            duration = 0
            width = 0
            height = 0
        
        # Prepare caption
        caption = f"**Jai Bajarangabali Episode {episode_number}**\n\n📺 Quality: 1080p\n💾 Size: {humanbytes(file_size)}\n⏱ Duration: {convert(int(duration))}"
        
        # Upload to channel
        await status_msg.edit("📤 Uploading to channel...")
        
        upload_client = app if app and Config.STRING_SESSION else client
        
        await upload_client.send_video(
            JAI_BAJARANGABALI_CHANNEL,
            video=video_path,
            caption=caption,
            thumb=thumb_path if thumb_success else None,
            duration=int(duration),
            width=width,
            height=height,
            progress=progress_for_pyrogram,
            progress_args=("📤 Uploading...", status_msg, time.time())
        )
        
        await status_msg.edit(
            f"✅ **Auto-Trim Complete!**\n\n"
            f"**File:** {new_filename}\n"
            f"**Episode:** {episode_number}\n"
            f"**Size:** {humanbytes(file_size)}\n"
            f"**Duration:** {convert(int(duration))}\n"
            f"**Segments:** {len(calculate_trim_segments(appearances, duration))}\n\n"
            f"✓ Uploaded to Jai Bajarangabali Channel"
        )
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Upload error: {e}\n{error_trace}")
        await status_msg.edit(f"❌ **Upload failed:** `{str(e)}`")
    
    finally:
        # Cleanup
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(original_path):
                os.remove(original_path)
            if thumb_success and os.path.exists(thumb_path):
                os.remove(thumb_path)
        except:
            pass
        
        # Remove state
        del autotrim_states[user_id]


@Client.on_message(filters.private & filters.command("autotrimhelp"))
async def autotrim_help(client, message):
    """Show help for autotrim feature"""
    help_text = """<b>✂️ AUTO-TRIM FEATURE</b>

<b>What it does:</b>
Automatically detects and removes all intro title cards from Jai Bajarangabali episodes, keeping only the actual episode content.

<b>Usage:</b>
<code>/autotrim <video_link></code>

<b>Example:</b>
<code>/autotrim https://example.com/jai-bajarangabali-ep11.mp4</code>

<b>Process:</b>
1. Bot downloads the video
2. Detects all intro title card appearances
3. Trims video to remove unnecessary cards
4. Merges trimmed segments
5. Asks for filename
6. Generates custom thumbnail with episode number
7. Uploads to Jai Bajarangabali channel

<b>Features:</b>
✓ Automatic intro detection
✓ Smart trimming (keeps 1st, removes others)
✓ Episode number extraction
✓ Custom thumbnail generation
✓ Direct channel upload
✓ Progress tracking

<b>Requirements:</b>
• Video must contain intro title cards
• At least 2 appearances required
• Video should be Jai Bajarangabali episode

<b>Configuration:</b>
Intro template URL: Set in environment variable
<code>INTRO_TITLE_VIDEO</code>

Upload to: Jai Bajarangabali Channel

<b>Note:</b> This feature is specifically designed for Jai Bajarangabali serial episodes.</b>"""
    
    await message.reply_text(help_text, disable_web_page_preview=True)
