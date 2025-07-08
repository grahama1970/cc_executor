#!/usr/bin/env python3
"""Run just the game engine competition test with reporting."""
import asyncio
from executor import test_game_engine_algorithm_competition

async def main():
    print("Running Game Engine Algorithm Competition Test...")
    print("This will take 10-15 minutes due to complex orchestration")
    print("="*80)
    
    try:
        result = await test_game_engine_algorithm_competition()
        if result:
            print("\n✅ Test completed successfully!")
            print("Check tmp/responses/ for the assessment report")
        else:
            print("\n❌ Test failed or returned no result")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())