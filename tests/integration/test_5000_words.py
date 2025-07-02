#!/usr/bin/env python3
"""Test the 5000 word story - the original truncation issue"""

import asyncio
import json
import sys
sys.path.insert(0, 'src')

from cc_executor.core.process_manager import ProcessManager
from cc_executor.core.stream_handler import StreamHandler

async def test_5000_word_story():
    """Test the exact command that was truncating before"""
    
    print("=" * 80)
    print("TESTING 5000 WORD STORY - ORIGINAL TRUNCATION ISSUE")
    print("=" * 80)
    
    process_manager = ProcessManager()
    stream_handler = StreamHandler()
    
    # The exact command from the websocket_handler.py docstring
    command = '''claude -p --output-format stream-json --verbose "Write a 5000 word science fiction story about a programmer who discovers their code is sentient. Include dialogue, plot twists, and a surprising ending. Stream the entire story."'''
    
    print(f"\nCommand: {command[:100]}...")
    print("\nStarting Claude...")
    start_time = asyncio.get_event_loop().time()
    
    process = await process_manager.execute_command(command)
    
    # Collect all output
    output_lines = []
    total_bytes = 0
    word_count = 0
    story_content = []
    
    async def collect_output(stream_type: str, data: str):
        nonlocal total_bytes, word_count
        if data.strip():
            output_lines.append(data.strip())
            total_bytes += len(data)
            
            # Try to parse Claude's JSON response
            try:
                claude_data = json.loads(data.strip())
                if claude_data.get("type") == "assistant":
                    content = claude_data.get("message", {}).get("content", [])
                    for item in content:
                        if item.get("type") == "text":
                            text = item["text"]
                            story_content.append(text)
                            words_in_chunk = len(text.split())
                            word_count += words_in_chunk
                            print(f"\n[Received {words_in_chunk} words, total so far: {word_count}]")
                            # Show first 200 chars of each chunk
                            preview = text[:200] + "..." if len(text) > 200 else text
                            print(f"Preview: {preview}")
                            
            except json.JSONDecodeError:
                # Not JSON, might be other output
                pass
            
    # Stream with a long timeout for story generation
    print("\nStreaming output...")
    await stream_handler.multiplex_streams(
        process.stdout,
        process.stderr,
        collect_output,
        timeout=None  # No timeout for long stories
    )
    
    exit_code = await process.wait()
    duration = asyncio.get_event_loop().time() - start_time
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(f"Exit code: {exit_code}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Total output lines: {len(output_lines)}")
    print(f"Total bytes received: {total_bytes:,}")
    print(f"Total words in story: {word_count:,}")
    
    # Check if we got a full story
    full_story = "\n\n".join(story_content)
    actual_word_count = len(full_story.split())
    
    print(f"\nStory statistics:")
    print(f"- Chunks received: {len(story_content)}")
    print(f"- Total story length: {len(full_story):,} characters")
    print(f"- Actual word count: {actual_word_count:,} words")
    
    if actual_word_count >= 4000:  # Allow some variance from exactly 5000
        print("\n✅ SUCCESS: Full story received without truncation!")
    else:
        print(f"\n❌ TRUNCATED: Only received {actual_word_count} words (expected ~5000)")
    
    # Save the story to verify
    with open("/tmp/claude_5000_word_story.txt", "w") as f:
        f.write(full_story)
    print("\nStory saved to: /tmp/claude_5000_word_story.txt")
    
    # Show the beginning and end of the story
    if full_story:
        print("\n" + "-" * 40)
        print("STORY BEGINNING:")
        print("-" * 40)
        print(full_story[:500] + "...")
        
        print("\n" + "-" * 40)
        print("STORY ENDING:")
        print("-" * 40)
        print("..." + full_story[-500:])
    
    return exit_code == 0 and actual_word_count >= 4000


if __name__ == "__main__":
    success = asyncio.run(test_5000_word_story())
    if not success:
        print("\n⚠️  The story was truncated or failed!")
        print("Check if our 8MB buffer is sufficient for very long Claude responses.")