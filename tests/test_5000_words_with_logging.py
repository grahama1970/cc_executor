#!/usr/bin/env python3
"""Test the 5000 word story with robust logging"""

import asyncio
import json
import sys
import time
from datetime import datetime

sys.path.insert(0, 'src')

from cc_executor.core.process_manager import ProcessManager
from cc_executor.core.stream_handler import StreamHandler
from loguru import logger

# Configure logging
logger.add("/tmp/5000_word_test_detailed.log", level="DEBUG")

async def test_5000_word_story():
    """Test the exact command that was truncating before"""
    
    test_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n{test_id}")
    print("=" * 80)
    print("TESTING 5000 WORD STORY WITH ROBUST LOGGING")
    print("=" * 80)
    
    process_manager = ProcessManager()
    stream_handler = StreamHandler()
    
    # The exact command that was causing issues
    command = 'claude -p --output-format stream-json --verbose "Write a 5000 word science fiction story about a programmer who discovers their code is sentient. Include dialogue, plot twists, and a surprising ending. Stream the entire story."'
    
    print(f"\nCommand: {command[:100]}...")
    logger.info(f"{test_id} - Starting test with command: {command}")
    
    print("\nStarting Claude...")
    start_time = time.time()
    
    process = await process_manager.execute_command(command)
    print(f"Process started: PID {process.pid}")
    logger.info(f"{test_id} - Process started with PID: {process.pid}")
    
    # Collect all output
    output_lines = []
    total_bytes = 0
    word_count = 0
    story_chunks = []
    last_progress = time.time()
    
    async def collect_output(stream_type: str, data: str):
        nonlocal total_bytes, word_count, last_progress
        
        if data.strip():
            output_lines.append(data.strip())
            total_bytes += len(data)
            
            # Log raw data
            logger.debug(f"{test_id} - {stream_type}: {len(data)} bytes")
            
            # Show progress every 5 seconds
            now = time.time()
            if now - last_progress > 5:
                elapsed = now - start_time
                print(f"[{elapsed:.1f}s] Received {total_bytes:,} bytes so far...")
                logger.info(f"{test_id} - Progress: {elapsed:.1f}s, {total_bytes:,} bytes")
                last_progress = now
            
            # Try to parse Claude's JSON response
            try:
                claude_data = json.loads(data.strip())
                msg_type = claude_data.get("type")
                
                if msg_type == "assistant":
                    content = claude_data.get("message", {}).get("content", [])
                    for item in content:
                        if item.get("type") == "text":
                            text = item["text"]
                            story_chunks.append(text)
                            words_in_chunk = len(text.split())
                            word_count += words_in_chunk
                            
                            elapsed = time.time() - start_time
                            print(f"\n[{elapsed:.1f}s] Received {words_in_chunk} words, total: {word_count}")
                            logger.info(f"{test_id} - Story chunk: {words_in_chunk} words, total: {word_count}")
                            
                            # Show preview
                            preview = text[:100] + "..." if len(text) > 100 else text
                            print(f"Preview: {preview}")
                            
                elif msg_type == "result":
                    # Log completion stats
                    duration_ms = claude_data.get("duration_ms", 0)
                    api_ms = claude_data.get("duration_api_ms", 0)
                    print(f"\nClaude completed: {duration_ms/1000:.1f}s total, {api_ms/1000:.1f}s API")
                    logger.info(f"{test_id} - Claude completed: {duration_ms}ms total, {api_ms}ms API")
                    
            except json.JSONDecodeError:
                # Not JSON, log it anyway
                logger.debug(f"{test_id} - Non-JSON output: {data[:100]}")
    
    # Stream with NO timeout for long stories
    print("\nStreaming output (no timeout - will wait for completion)...")
    logger.info(f"{test_id} - Starting stream with no timeout")
    
    try:
        await stream_handler.multiplex_streams(
            process.stdout,
            process.stderr,
            collect_output,
            timeout=None  # No timeout
        )
    except Exception as e:
        logger.error(f"{test_id} - Stream error: {e}")
        print(f"\nStream error: {e}")
    
    exit_code = await process.wait()
    duration = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(f"Test ID: {test_id}")
    print(f"Exit code: {exit_code}")
    print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"Total output lines: {len(output_lines)}")
    print(f"Total bytes received: {total_bytes:,}")
    print(f"Total words in story: {word_count:,}")
    
    logger.info(f"{test_id} - Final results: exit_code={exit_code}, duration={duration:.1f}s, bytes={total_bytes}, words={word_count}")
    
    # Check if we got a full story
    full_story = "\n\n".join(story_chunks)
    actual_word_count = len(full_story.split())
    
    print(f"\nStory statistics:")
    print(f"- Chunks received: {len(story_chunks)}")
    print(f"- Total story length: {len(full_story):,} characters")
    print(f"- Actual word count: {actual_word_count:,} words")
    
    success = False
    if actual_word_count >= 4000:  # Allow some variance from exactly 5000
        print("\n✅ SUCCESS: Full story received without truncation!")
        logger.info(f"{test_id} - SUCCESS: {actual_word_count} words received")
        success = True
    else:
        print(f"\n❌ TRUNCATED: Only received {actual_word_count} words (expected ~5000)")
        logger.error(f"{test_id} - TRUNCATED: Only {actual_word_count} words")
    
    # Save the story to verify
    story_file = f"/tmp/claude_5000_word_story_{test_id}.txt"
    with open(story_file, "w") as f:
        f.write(f"Test ID: {test_id}\n")
        f.write(f"Duration: {duration:.1f}s\n")
        f.write(f"Word count: {actual_word_count}\n")
        f.write("=" * 80 + "\n\n")
        f.write(full_story)
    print(f"\nStory saved to: {story_file}")
    
    # Show preview of story
    if full_story:
        print("\n" + "-" * 40)
        print("STORY BEGINNING:")
        print("-" * 40)
        print(full_story[:300] + "...")
        
        if len(full_story) > 600:
            print("\n" + "-" * 40)
            print("STORY ENDING:")
            print("-" * 40)
            print("..." + full_story[-300:])
    
    print(f"\nDetailed log saved to: /tmp/5000_word_test_detailed.log")
    print(f"Unique test marker for transcript verification: {test_id}")
    
    return success


if __name__ == "__main__":
    print("Starting 5000 word story test...")
    print("This may take 5-10 minutes to complete.")
    print("Press Ctrl+C to interrupt.\n")
    
    try:
        success = asyncio.run(test_5000_word_story())
        if success:
            print("\n🎉 Test passed! No truncation detected.")
            sys.exit(0)
        else:
            print("\n⚠️  Test failed! Story was truncated.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(130)