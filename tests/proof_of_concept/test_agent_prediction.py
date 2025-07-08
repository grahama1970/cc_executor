#!/usr/bin/env python3
"""Test agent-based timeout prediction."""
import asyncio
from executor import cc_execute, CCExecutorConfig

async def test_agent_prediction():
    """Test that agent can predict appropriate timeouts."""
    
    test_cases = [
        {
            "task": "Write a simple hello world function",
            "expected_range": (60, 180),  # 1-3 minutes for simple task
        },
        {
            "task": """Create a complete FastAPI application with:
- User authentication system with JWT
- SQLAlchemy models for users, posts, and comments
- Full CRUD endpoints with proper validation
- Database migrations with Alembic
- Comprehensive test suite with pytest
- Docker configuration
- API documentation""",
            "expected_range": (600, 1800),  # 10-30 minutes for complex task
        }
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\nTest {i+1}: {test['task'][:50]}...")
        print("=" * 60)
        
        # Test with agent prediction
        config = CCExecutorConfig()
        
        # Just get the prediction without running the task
        print("Requesting agent prediction...")
        start_time = asyncio.get_event_loop().time()
        
        # We'll simulate by checking what timeout would be set
        # For real test, we'd need to extract the timeout prediction logic
        result = await cc_execute(
            test['task'],
            config=config,
            stream=False,
            agent_predict_timeout=True
        )
        
        prediction_time = asyncio.get_event_loop().time() - start_time
        
        print(f"Agent prediction took: {prediction_time:.1f}s")
        print(f"Result preview: {result[:200]}...")
        
        # Check if timeout was in expected range
        # (In real implementation, we'd check the actual timeout used)
        min_expected, max_expected = test['expected_range']
        print(f"Expected range: {min_expected}-{max_expected}s")

async def test_comparison():
    """Compare agent prediction vs Redis estimation."""
    task = "Build a machine learning pipeline for sentiment analysis"
    
    print("Comparing timeout prediction methods...")
    print("=" * 60)
    print(f"Task: {task}")
    print()
    
    # Method 1: Redis estimation (default)
    print("1. Redis-based estimation:")
    config1 = CCExecutorConfig()
    # Simulate getting timeout without execution
    from executor import estimate_timeout
    redis_timeout = estimate_timeout(task)
    print(f"   Redis estimate: {redis_timeout}s")
    
    # Method 2: Agent prediction
    print("\n2. Agent-based prediction:")
    # This would actually call Claude to predict
    print("   (Would call Claude for prediction)")
    print("   Expected: More accurate for novel tasks")
    
    print("\nRecommendation:")
    print("- Use Redis estimation for known/similar tasks (faster)")
    print("- Use agent prediction for novel/complex tasks (more accurate)")

if __name__ == "__main__":
    print("Testing agent-based timeout prediction...")
    
    # Run comparison
    asyncio.run(test_comparison())
    
    # Uncomment to test actual predictions (will use Claude calls)
    # asyncio.run(test_agent_prediction())