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
INTRO_TITLE_VIDEO_URL = os.environ.get("INTRO_TITLE_VIDEO", "https://envs.sh/3G7.mp4")
JAI_BAJARANGABALI_CHANNEL = -1002987317144
JAI_BAJARANGABALI_THUMB_BASE = "https://envs.sh/zcf.jpg"

# Temporary storage for user states
autotrim_states = {}


def log_step(step_name, details=""):
    """Enhanced logging function"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {step_name}"
    if details:
        log_msg += f" - {details}"
    print(log_msg)
    return log_msg


def download_intro_template(custom_url=None):
    """Download intro title template video"""
    try:
        intro_url = custom_url or INTRO_TITLE_VIDEO_URL
        log_step("DOWNLOAD_INTRO_TEMPLATE", f"URL: {intro_url}")
        
        template_path = "templates/intro_title.mp4"
        os.makedirs("templates", exist_ok=True)
        
        if not os.path.exists(template_path) or custom_url:
            log_step("DOWNLOAD_INTRO_TEMPLATE", "Starting download...")
            response = requests.get(intro_url, timeout=60, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(template_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            file_size = os.path.getsize(template_path)
            log_step("DOWNLOAD_INTRO_TEMPLATE", f"✓ Downloaded {humanbytes(file_size)}")
        else:
            log_step("DOWNLOAD_INTRO_TEMPLATE", "✓ Using cached template")
        
        return template_path
    except Exception as e:
        log_step("DOWNLOAD_INTRO_TEMPLATE", f"❌ ERROR: {e}")
        print(traceback.format_exc())
        return None


def extract_intro_frame(template_path):
    """Extract a frame from intro video for matching"""
    try:
        log_step("EXTRACT_INTRO_FRAME", f"Template: {template_path}")
        
        if not os.path.exists(template_path):
            log_step("EXTRACT_INTRO_FRAME", "❌ Template file not found")
            return None
        
        cap = cv2.VideoCapture(template_path)
        if not cap.isOpened():
            log_step("EXTRACT_INTRO_FRAME", "❌ Failed to open video")
            return None
        
        ret, frame = cap.read()
        cap.release()
        
        if ret and frame is not None:
            # Convert to grayscale for better matching
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            log_step("EXTRACT_INTRO_FRAME", f"✓ Frame extracted: {gray.shape}")
            return gray
        else:
            log_step("EXTRACT_INTRO_FRAME", "❌ Failed to read frame")
            return None
    except Exception as e:
        log_step("EXTRACT_INTRO_FRAME", f"❌ ERROR: {e}")
        print(traceback.format_exc())
        return None


def find_intro_appearances(video_path, template_frame, progress_callback=None):
    """Find all appearances of intro title card in video"""
    try:
        log_step("FIND_INTRO_APPEARANCES", f"Video: {video_path}")
        
        if not os.path.exists(video_path):
            log_step("FIND_INTRO_APPEARANCES", "❌ Video file not found")
            return [], 0, 0
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            log_step("FIND_INTRO_APPEARANCES", "❌ Failed to open video")
            return [], 0, 0
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        log_step("FIND_INTRO_APPEARANCES", f"Duration: {duration:.1f}s, Frames: {total_frames}, FPS: {fps:.1f}")
        
        appearances = []
        frame_count = 0
        last_match_frame = -100
        
        # Check every 5th frame for performance
        skip_frames = 5
        threshold = 0.70  # Lowered threshold for better detection
        
        last_progress_update = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % skip_frames == 0:
                try:
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
                        log_step("FIND_INTRO_APPEARANCES", f"✓ Found intro #{len(appearances)} at {timestamp:.1f}s (similarity: {max_val:.3f})")
                    
                    # Progress callback every 2 seconds
                    current_time = time.time()
                    if progress_callback and (current_time - last_progress_update) >= 2:
                        progress = (frame_count / total_frames) * 100
                        asyncio.create_task(progress_callback(progress, frame_count, total_frames))
                        last_progress_update = current_time
                
                except Exception as frame_error:
                    log_step("FIND_INTRO_APPEARANCES", f"Frame {frame_count} error: {frame_error}")
            
            frame_count += 1
        
        cap.release()
        log_step("FIND_INTRO_APPEARANCES", f"✓ Analysis complete: {len(appearances)} appearances found")
        
        return appearances, duration, fps
    
    except Exception as e:
        log_step("FIND_INTRO_APPEARANCES", f"❌ CRITICAL ERROR: {e}")
        print(traceback.format_exc())
        return [], 0, 0


def calculate_trim_segments(appearances, duration):
    """Calculate video segments to keep based on intro appearances"""
    log_step("CALCULATE_TRIM_SEGMENTS", f"Input: {len(appearances)} appearances, {duration:.1f}s duration")
    
    if len(appearances) < 2:
        log_step("CALCULATE_TRIM_SEGMENTS", "⚠️ Not enough appearances, keeping full video")
        return [(0, duration)]
    
    segments = []
    
    # Keep from start to before 2nd appearance
    if len(appearances) >= 2:
        segment = (0, appearances[1]['timestamp'] - 0.5)
        segments.append(segment)
        log_step("CALCULATE_TRIM_SEGMENTS", f"Segment 1: {segment[0]:.1f}s - {segment[1]:.1f}s")
    
    # Keep from after 3rd to before 4th appearance
    if len(appearances) >= 4:
        segment = (appearances[2]['timestamp'] + 5.0, appearances[3]['timestamp'] - 0.5)
        segments.append(segment)
        log_step("CALCULATE_TRIM_SEGMENTS", f"Segment 2: {segment[0]:.1f}s - {segment[1]:.1f}s")
    
    # Keep from after 5th to before 6th appearance
    if len(appearances) >= 6:
        segment = (appearances[4]['timestamp'] + 5.0, appearances[5]['timestamp'] - 0.5)
        segments.append(segment)
        log_step("CALCULATE_TRIM_SEGMENTS", f"Segment 3: {segment[0]:.1f}s - {segment[1]:.1f}s")
    
    # If only 4 appearances, keep from after 3rd to end
    elif len(appearances) == 4:
        segment = (appearances[2]['timestamp'] + 5.0, duration)
        segments.append(segment)
        log_step("CALCULATE_TRIM_SEGMENTS", f"Segment 2 (to end): {segment[0]:.1f}s - {segment[1]:.1f}s")
    
    total_duration = sum(end - start for start, end in segments)
    log_step("CALCULATE_TRIM_SEGMENTS", f"✓ Total segments: {len(segments)}, Total duration: {total_duration:.1f}s")
    
    return segments


async def trim_and_merge_video(video_path, segments, output_path, progress_callback=None):
    """Trim video into segments and merge them"""
    try:
        log_step("TRIM_AND_MERGE", f"Input: {video_path}, Output: {output_path}")
        log_step("TRIM_AND_MERGE", f"Segments: {len(segments)}")
        
        segment_files = []
        segments_dir = "downloads/segments"
        os.makedirs(segments_dir, exist_ok=True)
        
        # Create segment files
        for i, (start, end) in enumerate(segments, 1):
            segment_file = os.path.join(segments_dir, f"segment_{i}.mp4")
            
            log_step("TRIM_AND_MERGE", f"Extracting segment {i}: {start:.1f}s - {end:.1f}s")
            
            # FFmpeg command to extract segment
            cmd = f'ffmpeg -i "{video_path}" -ss {start} -to {end} -c copy -avoid_negative_ts 1 "{segment_file}" -y -loglevel error'
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                log_step("TRIM_AND_MERGE", f"❌ Segment {i} failed: {stderr.decode()}")
            elif os.path.exists(segment_file):
                size = os.path.getsize(segment_file)
                log_step("TRIM_AND_MERGE", f"✓ Segment {i} created: {humanbytes(size)}")
                segment_files.append(segment_file)
                
                if progress_callback:
                    progress = (i / len(segments)) * 50
                    await progress_callback(progress)
            else:
                log_step("TRIM_AND_MERGE", f"❌ Segment {i} not created")
        
        if not segment_files:
            log_step("TRIM_AND_MERGE", "❌ No segments created")
            return False
        
        # Create concat file for ffmpeg
        concat_file = os.path.join(segments_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            for seg_file in segment_files:
                f.write(f"file '{os.path.abspath(seg_file)}'\n")
        
        log_step("TRIM_AND_MERGE", f"Merging {len(segment_files)} segments...")
        
        # Merge segments
        merge_cmd = f'ffmpeg -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}" -y -loglevel error'
        
        process = await asyncio.create_subprocess_shell(
            merge_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            log_step("TRIM_AND_MERGE", f"❌ Merge failed: {stderr.decode()}")
        
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
        
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            log_step("TRIM_AND_MERGE", f"✓ Final video created: {humanbytes(size)}")
            return True
        else:
            log_step("TRIM_AND_MERGE", "❌ Final video not created")
            return False
    
    except Exception as e:
        log_step("TRIM_AND_MERGE", f"❌ ERROR: {e}")
        print(traceback.format_exc())
        return False


def generate_thumbnail_with_episode(base_thumb_url, episode_number, output_path):
    """Generate thumbnail with episode number overlay"""
    try:
        log_step("GENERATE_THUMBNAIL", f"Episode: {episode_number}")
        
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
        
        log_step("GENERATE_THUMBNAIL", f"✓ Thumbnail created: {output_path}")
        return True
    except Exception as e:
        log_step("GENERATE_THUMBNAIL", f"❌ ERROR: {e}")
        return False


@Client.on_message(filters.private & filters.command(["autotrim"]))
async def autotrim_command(client, message: Message):
    """Handle autotrim command"""
    user_id = message.from_user.id
    
    try:
        log_step("AUTOTRIM_COMMAND", f"User: {user_id}, Message: {message.text}")
        
        # Extract video link and optional intro link
        parts = message.text.split()
        if len(parts) < 2:
            return await message.reply_text(
                "**Usage:**\n"
                "`/autotrim <video_link>`\n"
                "OR\n"
                "`/autotrim <video_link> <intro_title_link>`\n\n"
                "**Example:**\n"
                "`/autotrim https://example.com/jai-bajarangabali-ep11.mp4`\n"
                "`/autotrim https://example.com/video.mp4 https://example.com/intro.mp4`\n\n"
                "This will automatically trim the video and remove all intro title cards except the first one."
            )
        
        video_url = parts[1].strip()
        intro_url = parts[2].strip() if len(parts) >= 3 else None
        
        log_step("AUTOTRIM_COMMAND", f"Video URL: {video_url}")
        if intro_url:
            log_step("AUTOTRIM_COMMAND", f"Custom Intro URL: {intro_url}")
        
        # Validate URL
        if not video_url.startswith('http'):
            return await message.reply_text("❌ Invalid video URL! Please provide a valid link.")
        
        if intro_url and not intro_url.startswith('http'):
            return await message.reply_text("❌ Invalid intro URL! Please provide a valid link.")
        
        # Start processing
        status_msg = await message.reply_text(
            "🔧 **Auto-Trim Started!**\n\n"
            "⏳ Step 1/6: Preparing intro template..."
        )
        
        # Download intro template
        log_step("MAIN_PROCESS", "Step 1/6: Downloading intro template")
        template_path = download_intro_template(intro_url)
        if not template_path:
            log_step("MAIN_PROCESS", "❌ Step 1 failed")
            return await status_msg.edit("❌ Failed to download intro template!")
        
        # Extract intro frame
        log_step("MAIN_PROCESS", "Step 2/6: Extracting intro frame")
        await status_msg.edit(
            "🔧 **Auto-Trim Started!**\n\n"
            "⏳ Step 2/6: Extracting intro frame..."
        )
        
        template_frame = extract_intro_frame(template_path)
        if template_frame is None:
            log_step("MAIN_PROCESS", "❌ Step 2 failed")
            return await status_msg.edit("❌ Failed to extract intro frame!")
        
        # Download video
        log_step("MAIN_PROCESS", "Step 3/6: Downloading video")
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
            log_step("DOWNLOAD_VIDEO", f"Starting download from: {video_url}")
            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            last_update = 0
            
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update every 5MB
                        if total_size > 0 and (downloaded - last_update) >= (5 * 1024 * 1024):
                            progress = (downloaded / total_size) * 100
                            last_update = downloaded
                            try:
                                await status_msg.edit(
                                    f"🔧 **Auto-Trim Started!**\n\n"
                                    f"📥 Step 3/6: Downloading video...\n"
                                    f"Progress: {progress:.1f}% ({humanbytes(downloaded)}/{humanbytes(total_size)})"
                                )
                            except:
                                pass
            
            log_step("DOWNLOAD_VIDEO", f"✓ Downloaded: {humanbytes(os.path.getsize(video_path))}")
        except Exception as e:
            log_step("DOWNLOAD_VIDEO", f"❌ ERROR: {e}")
            return await status_msg.edit(f"❌ Download failed: {str(e)}")
        
        if not os.path.exists(video_path):
            log_step("DOWNLOAD_VIDEO", "❌ File not found after download")
            return await status_msg.edit("❌ Video download failed!")
        
        # Find intro appearances
        log_step("MAIN_PROCESS", "Step 4/6: Analyzing video")
        await status_msg.edit(
            "🔧 **Auto-Trim Started!**\n\n"
            "🔍 Step 4/6: Analyzing video for intro cards...\n"
            "This may take a few minutes..."
        )
        
        async def analysis_progress(progress, current_frame, total_frames):
            try:
                await status_msg.edit(
                    f"🔧 **Auto-Trim Started!**\n\n"
                    f"🔍 Step 4/6: Analyzing video...\n"
                    f"Progress: {progress:.1f}% ({current_frame}/{total_frames} frames)\n"
                    f"⏱ Please wait..."
                )
            except Exception as e:
                log_step("ANALYSIS_PROGRESS", f"Update failed: {e}")
        
        appearances, duration, fps = find_intro_appearances(video_path, template_frame, analysis_progress)
        
        log_step("MAIN_PROCESS", f"Analysis complete: {len(appearances)} appearances")
        
        if len(appearances) < 2:
            os.remove(video_path)
            log_step("MAIN_PROCESS", "❌ Insufficient appearances found")
            return await status_msg.edit(
                f"⚠️ **Insufficient intro cards found!**\n\n"
                f"Found: {len(appearances)} appearances\n"
                f"Required: At least 2\n\n"
                f"Detected at:\n" +
                ("\n".join([f"• {i+1}. {app['timestamp']:.1f}s (sim: {app['similarity']:.2f})" for i, app in enumerate(appearances)]) if appearances else "None") +
                f"\n\nPlease check if this is the correct video."
            )
        
        await status_msg.edit(
            f"✅ **Analysis Complete!**\n\n"
            f"📊 Found {len(appearances)} intro card appearances:\n" +
            "\n".join([f"• {i+1}. At {app['timestamp']:.1f}s (sim: {app['similarity']:.2f})" for i, app in enumerate(appearances[:6])]) +
            f"\n\n✂️ Step 5/6: Trimming and merging..."
        )
        
        # Calculate trim segments
        log_step("MAIN_PROCESS", "Step 5/6: Trimming video")
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
            log_step("MAIN_PROCESS", "❌ Trimming failed")
            return await status_msg.edit("❌ Video trimming failed!")
        
        log_step("MAIN_PROCESS", "✓ Trimming complete")
        
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
            'appearances': appearances,
            'segments': segments
        }
        
        log_step("MAIN_PROCESS", "✓ Waiting for filename input")
    
    except Exception as e:
        error_trace = traceback.format_exc()
        log_step("AUTOTRIM_COMMAND", f"❌ CRITICAL ERROR: {e}")
        print(error_trace)
        await message.reply_text(f"❌ **Error:** `{str(e)}`")


@Client.on_message(filters.private & filters.text & ~filters.command(["autotrim", "autotrimhelp", "autotrimstatus", "autotrimcancel", "start", "help"]))
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
    segments = state.get('segments', [])
    
    try:
        log_step("HANDLE_FILENAME", f"User: {user_id}, Filename: {message.text}")
        
        new_filename = message.text.strip()
        
        # Extract episode number from filename
        episode_match = re.search(r'(?:Episode|Ep|E)\s*(\d+)', new_filename, re.IGNORECASE)
        episode_number = episode_match.group(1) if episode_match else "1"
        
        log_step("HANDLE_FILENAME", f"Episode number: {episode_number}")
        
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
            fps_value = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps_value if fps_value > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            log_step("HANDLE_FILENAME", f"Video metadata: {width}x{height}, {duration:.1f}s")
        except:
            duration = 0
            width = 0
            height = 0
        
        # Prepare caption
        caption = (
            f"**Jai Bajarangabali Episode {episode_number}**\n\n"
            f"📺 Quality: 1080p\n"
            f"💾 Size: {humanbytes(file_size)}\n"
            f"⏱ Duration: {convert(int(duration))}\n"
            f"✂️ Segments: {len(segments)}"
        )
        
        # Upload to channel
        log_step("HANDLE_FILENAME", "Starting upload to channel")
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
        
        log_step("HANDLE_FILENAME", "✓ Upload complete")
        
        await status_msg.edit(
            f"✅ **Auto-Trim Complete!**\n\n"
            f"**File:** {new_filename}\n"
            f"**Episode:** {episode_number}\n"
            f"**Size:** {humanbytes(file_size)}\n"
            f"**Duration:** {convert(int(duration))}\n"
            f"**Segments:** {len(segments)}\n"
            f"**Intro cards found:** {len(appearances)}\n\n"
            f"✓ Uploaded to Jai Bajarangabali Channel"
        )
    
    except Exception as e:
        error_trace = traceback.format_exc()
        log_step("HANDLE_FILENAME", f"❌ ERROR: {e}")
        print(error_trace)
        await status_msg.edit(f"❌ **Upload failed:** `{str(e)}`")
    
    finally:
        # Cleanup
        log_step("CLEANUP", "Removing temporary files")
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                log_step("CLEANUP", f"✓ Removed: {video_path}")
            if os.path.exists(original_path):
                os.remove(original_path)
                log_step("CLEANUP", f"✓ Removed: {original_path}")
            if thumb_success and os.path.exists(thumb_path):
                os.remove(thumb_path)
                log_step("CLEANUP", f"✓ Removed: {thumb_path}")
        except Exception as cleanup_error:
            log_step("CLEANUP", f"⚠️ Cleanup error: {cleanup_error}")
        
        # Remove state
        del autotrim_states[user_id]
        log_step("CLEANUP", f"✓ User state cleared for {user_id}")


@Client.on_message(filters.private & filters.command(["autotrimhelp"]))
async def autotrim_help(client, message):
    """Show help for autotrim feature"""
    help_text = """<b>✂️ AUTO-TRIM FEATURE</b>

<b>What it does:</b>
Automatically detects and removes all intro title cards from Jai Bajarangabali episodes, keeping only the actual episode content.

<b>Usage:</b>
<code>/autotrim &lt;video_link&gt;</code>
OR
<code>/autotrim &lt;video_link&gt; &lt;intro_title_link&gt;</code>

<b>Examples:</b>
<code>/autotrim https://example.com/jai-bajarangabali-ep11.mp4</code>

<code>/autotrim https://example.com/video.mp4 https://example.com/intro.mp4</code>

<b>Process:</b>
1. Bot downloads the intro template (default or custom)
2. Bot downloads the video
3. Detects all intro title card appearances
4. Trims video to remove unnecessary cards
5. Merges trimmed segments
6. Asks for filename
7. Generates custom thumbnail with episode number
8. Uploads to Jai Bajarangabali channel

<b>Features:</b>
✓ Automatic intro detection using template matching
✓ Smart trimming (keeps 1st intro, removes others)
✓ Custom intro template support
✓ Episode number extraction from filename
✓ Custom thumbnail generation with episode overlay
✓ Direct channel upload
✓ Real-time progress tracking
✓ Detailed logging for debugging

<b>Trimming Logic:</b>
• If 2 appearances: Keep start to before 2nd
• If 4 appearances: Keep start to before 2nd, then after 3rd to end
• If 6+ appearances: Keep start to before 2nd, after 3rd to before 4th, after 5th to before 6th

<b>Requirements:</b>
• Video must contain intro title cards
• At least 2 appearances required for trimming
• Video should be Jai Bajarangabali episode (or similar format)
• Stable internet connection for downloads

<b>Configuration:</b>
• Default intro template: Set in <code>INTRO_TITLE_VIDEO</code> environment variable
• Upload channel: Jai Bajarangabali Channel
• Base thumbnail: <code>JAI_BAJARANGABALI_THUMB_BASE</code>

<b>Troubleshooting:</b>
If analysis gets stuck at Step 4:
1. Check if video file is valid
2. Verify intro template is correct
3. Check console logs for detailed errors
4. Try with custom intro URL parameter

<b>Debug Mode:</b>
All operations are logged with timestamps in the console. Check logs for:
• DOWNLOAD_INTRO_TEMPLATE
• EXTRACT_INTRO_FRAME
• FIND_INTRO_APPEARANCES
• CALCULATE_TRIM_SEGMENTS
• TRIM_AND_MERGE
• HANDLE_FILENAME

<b>Note:</b> 
This feature is specifically designed for Jai Bajarangabali serial episodes but can be adapted for any video with repetitive intro cards.

<b>Performance:</b>
• Analysis checks every 5th frame for efficiency
• Similarity threshold: 70% (adjustable)
• Progress updates every 2 seconds
• Automatic cleanup of temporary files

<b>Support:</b>
If you encounter issues, check the console logs for detailed error messages and timestamps.</b>"""
    
    await message.reply_text(help_text, disable_web_page_preview=True)


@Client.on_message(filters.private & filters.command(["autotrimstatus"]))
async def autotrim_status(client, message: Message):
    """Check autotrim processing status"""
    user_id = message.from_user.id
    
    if user_id in autotrim_states:
        state = autotrim_states[user_id]
        await message.reply_text(
            f"✅ **Active Auto-Trim Session**\n\n"
            f"📁 Video: `{os.path.basename(state['video_path'])}`\n"
            f"📊 Appearances: {len(state['appearances'])}\n"
            f"✂️ Segments: {len(state.get('segments', []))}\n\n"
            f"⏳ Waiting for filename input..."
        )
    else:
        await message.reply_text(
            "ℹ️ **No Active Session**\n\n"
            "You don't have any active auto-trim session.\n"
            "Use `/autotrim <video_link>` to start."
        )


@Client.on_message(filters.private & filters.command(["autotrimcancel"]))
async def autotrim_cancel(client, message: Message):
    """Cancel current autotrim session"""
    user_id = message.from_user.id
    
    if user_id in autotrim_states:
        state = autotrim_states[user_id]
        
        # Cleanup files
        try:
            if os.path.exists(state['video_path']):
                os.remove(state['video_path'])
            if os.path.exists(state['original_path']):
                os.remove(state['original_path'])
        except:
            pass
        
        # Remove state
        del autotrim_states[user_id]
        
        log_step("AUTOTRIM_CANCEL", f"Session cancelled by user {user_id}")
        
        await message.reply_text(
            "✅ **Session Cancelled**\n\n"
            "Your auto-trim session has been cancelled and temporary files have been removed."
        )
    else:
        await message.reply_text(
            "ℹ️ **No Active Session**\n\n"
            "You don't have any active session to cancel."
        )


# Startup log
log_step("MODULE_LOADED", "Auto-Trim module initialized successfully")
log_step("CONFIG", f"Intro template URL: {INTRO_TITLE_VIDEO_URL}")
log_step("CONFIG", f"Target channel: {JAI_BAJARANGABALI_CHANNEL}")
log_step("CONFIG", f"Base thumbnail: {JAI_BAJARANGABALI_THUMB_BASE}")


# Test command to verify handlers are working
@Client.on_message(filters.private & filters.command(["autotrimtest"]))
async def autotrim_test(client, message: Message):
    """Test if autotrim module is loaded and working"""
    await message.reply_text(
        "✅ **Auto-Trim Module Active**\n\n"
        f"📝 Available Commands:\n"
        f"• /autotrim - Start auto-trim\n"
        f"• /autotrimhelp - Show help\n"
        f"• /autotrimstatus - Check status\n"
        f"• /autotrimcancel - Cancel session\n\n"
        f"🔧 Configuration:\n"
        f"• Channel: `{JAI_BAJARANGABALI_CHANNEL}`\n"
        f"• Template: `{INTRO_TITLE_VIDEO_URL}`\n\n"
        f"Active sessions: {len(autotrim_states)}"
    )
