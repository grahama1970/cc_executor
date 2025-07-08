#!/usr/bin/env python3
"""
Advanced examples for CC Executor.
Demonstrates complex concurrent task execution like the game engine algorithm competition.
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from executor import cc_execute, cc_execute_list, CCExecutorConfig


async def game_engine_algorithm_competition():
    """
    Spawn 3 different Claude instances to create more efficient algorithms
    than the fast inverse square root algorithm.
    """
    print("=== Game Engine Algorithm Competition ===")
    print("Challenge: Create a more efficient algorithm than fast inverse square root")
    print("Running 3 Claude instances concurrently...\n")
    
    # Define 3 different approaches for the competition
    tasks = [
        {
            "approach": "Mathematical Optimization",
            "prompt": """Create a more efficient algorithm than the fast inverse square root 
for game engines. Focus on mathematical optimizations and modern CPU features.
Requirements:
1. Must be faster than the classic Quake III algorithm
2. Maintain or improve accuracy
3. Provide benchmarks comparing to the original
4. Include both C and Python implementations
5. Explain the mathematical principles used"""
        },
        {
            "approach": "SIMD/Vectorization",
            "prompt": """Create a more efficient algorithm than the fast inverse square root 
using SIMD instructions and vectorization techniques.
Requirements:
1. Utilize modern CPU vector instructions (SSE, AVX)
2. Process multiple values in parallel
3. Provide benchmarks showing improvement
4. Include intrinsics-based C implementation
5. Explain how vectorization improves performance"""
        },
        {
            "approach": "Hardware-Specific Optimization",
            "prompt": """Create a more efficient algorithm than the fast inverse square root
optimized for modern GPU and specialized hardware.
Requirements:
1. Target GPU compute capabilities
2. Consider cache hierarchies and memory access patterns
3. Provide CUDA/OpenCL implementation
4. Benchmark on different hardware
5. Explain hardware-specific optimizations"""
        }
    ]
    
    # Configure for longer timeout since these are complex tasks
    config = CCExecutorConfig(
        timeout=600,  # 10 minutes per approach
        stream_output=True
    )
    
    # Execute all three approaches concurrently
    start_time = time.time()
    
    # Create tasks for concurrent execution
    async def execute_approach(approach_info):
        """Execute a single approach and return results."""
        print(f"[{approach_info['approach']}] Starting...")
        result = await cc_execute(approach_info['prompt'], config)
        print(f"\n[{approach_info['approach']}] Completed!")
        return {
            "approach": approach_info['approach'],
            "result": result,
            "execution_time": time.time() - start_time
        }
    
    # Run all three concurrently
    results = await asyncio.gather(
        *[execute_approach(task) for task in tasks]
    )
    
    # Save competition results
    competition_dir = Path(__file__).parent / "tmp" / "competition_results"
    competition_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save individual results
    for i, result in enumerate(results):
        result_file = competition_dir / f"approach_{i+1}_{timestamp}.md"
        result_file.write_text(
            f"# {result['approach']}\n\n"
            f"Execution time: {result['execution_time']:.2f}s\n\n"
            f"## Solution\n\n{result['result']}"
        )
    
    # Create summary report
    summary = competition_dir / f"competition_summary_{timestamp}.md"
    summary_content = f"""# Game Engine Algorithm Competition Results

**Date**: {datetime.now()}
**Total execution time**: {time.time() - start_time:.2f}s

## Approaches Tested

"""
    
    for i, result in enumerate(results):
        summary_content += f"""
### {i+1}. {result['approach']}
- Execution time: {result['execution_time']:.2f}s
- Output length: {len(result['result'])} characters
- File: approach_{i+1}_{timestamp}.md

"""
    
    summary.write_text(summary_content)
    
    print(f"\n✅ Competition complete! Results saved to {competition_dir}")
    print(f"Total time: {time.time() - start_time:.2f}s")
    
    return results


async def distributed_web_scraper():
    """
    Create a distributed web scraper using multiple Claude instances.
    Each instance handles a different aspect of the scraping system.
    """
    print("\n=== Distributed Web Scraper Example ===")
    
    components = [
        "Create an async URL queue manager with Redis for distributing URLs across workers",
        "Implement a content parser that extracts structured data from HTML using BeautifulSoup",
        "Build a rate limiter and robots.txt respecter to ensure ethical scraping",
        "Create a data pipeline that cleans, validates, and stores scraped data in PostgreSQL"
    ]
    
    # Execute components concurrently
    config = CCExecutorConfig(timeout=300, stream_output=False)
    
    print("Building distributed scraper components concurrently...")
    results = await cc_execute_list(components, config, sequential=False)
    
    # Combine results into a single system
    combined_file = Path(__file__).parent / "tmp" / "distributed_scraper.py"
    combined_content = "#!/usr/bin/env python3\n\"\"\"\nDistributed Web Scraper System\n"
    combined_content += "Generated by concurrent Claude instances\n\"\"\"\n\n"
    
    for component, result in zip(components, results):
        combined_content += f"\n# {'='*60}\n# {component}\n# {'='*60}\n\n{result}\n"
    
    combined_file.write_text(combined_content)
    print(f"✅ Combined scraper saved to: {combined_file}")
    
    return results


async def microservices_architecture():
    """
    Design a complete microservices architecture with multiple Claude instances
    each responsible for a different service.
    """
    print("\n=== Microservices Architecture Example ===")
    
    services = {
        "auth-service": """Design an authentication microservice with:
- JWT token generation and validation
- User registration and login endpoints
- Password hashing with bcrypt
- Redis session management
- FastAPI implementation with async SQLAlchemy""",
        
        "payment-service": """Create a payment processing microservice with:
- Stripe integration for card payments
- Invoice generation and management
- Webhook handling for payment events
- Idempotency key support
- Database transactions with PostgreSQL""",
        
        "notification-service": """Build a notification microservice with:
- Email sending via SendGrid
- SMS via Twilio
- Push notifications setup
- Template management
- Message queue integration with RabbitMQ""",
        
        "api-gateway": """Implement an API gateway with:
- Request routing to microservices
- Rate limiting per client
- Authentication token validation
- Request/response transformation
- Circuit breaker pattern"""
    }
    
    config = CCExecutorConfig(
        timeout=600,
        stream_output=True
    )
    
    # Execute all services concurrently
    async def create_service(name, spec):
        print(f"[{name}] Generating service specification...")
        result = await cc_execute(spec, config)
        return {name: result}
    
    results = await asyncio.gather(
        *[create_service(name, spec) for name, spec in services.items()]
    )
    
    # Save each service
    services_dir = Path(__file__).parent / "tmp" / "microservices"
    services_dir.mkdir(parents=True, exist_ok=True)
    
    for service_result in results:
        for name, code in service_result.items():
            service_file = services_dir / f"{name}.py"
            service_file.write_text(code)
            print(f"✅ Saved {name} to {service_file}")
    
    # Create docker-compose.yml
    docker_compose = services_dir / "docker-compose.yml"
    docker_content = """version: '3.8'

services:
"""
    for service_name in services.keys():
        docker_content += f"""
  {service_name}:
    build: ./{service_name}
    ports:
      - "{8000 + list(services.keys()).index(service_name)}:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/{service_name}
    depends_on:
      - db
      - redis
"""
    
    docker_content += """
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
"""
    
    docker_compose.write_text(docker_content)
    print(f"\n✅ Created docker-compose.yml for microservices")
    
    return results


async def machine_learning_pipeline():
    """
    Create a complete ML pipeline with different Claude instances handling
    different stages of the pipeline concurrently.
    """
    print("\n=== Machine Learning Pipeline Example ===")
    
    pipeline_stages = [
        {
            "stage": "Data Preprocessing",
            "task": """Create a data preprocessing module that:
1. Loads data from multiple sources (CSV, JSON, SQL)
2. Handles missing values with multiple strategies
3. Performs feature engineering (polynomial, interactions)
4. Scales and normalizes features
5. Splits data for training/validation/test
Include pandas and scikit-learn implementations."""
        },
        {
            "stage": "Model Training",
            "task": """Build a model training framework that:
1. Supports multiple algorithms (Random Forest, XGBoost, Neural Networks)
2. Implements hyperparameter tuning with Optuna
3. Handles cross-validation properly
4. Tracks experiments with MLflow
5. Saves best models with versioning
Include PyTorch and scikit-learn examples."""
        },
        {
            "stage": "Model Deployment",
            "task": """Create a model deployment system that:
1. Serves models via FastAPI endpoints
2. Implements model versioning and A/B testing
3. Monitors prediction performance
4. Handles batch and real-time inference
5. Includes auto-scaling capabilities
Use TorchServe and Docker."""
        }
    ]
    
    config = CCExecutorConfig(timeout=600)
    
    # Execute pipeline stages concurrently
    results = await asyncio.gather(
        *[cc_execute(stage["task"], config) for stage in pipeline_stages]
    )
    
    # Save ML pipeline
    ml_dir = Path(__file__).parent / "tmp" / "ml_pipeline"
    ml_dir.mkdir(parents=True, exist_ok=True)
    
    for stage, result in zip(pipeline_stages, results):
        stage_file = ml_dir / f"{stage['stage'].lower().replace(' ', '_')}.py"
        stage_file.write_text(result)
        print(f"✅ Saved {stage['stage']} to {stage_file}")
    
    return results


async def main():
    """Run all advanced examples."""
    print("CC Executor - Advanced Examples")
    print("="*50)
    print("Demonstrating concurrent Claude execution")
    print()
    
    # Run examples
    try:
        # 1. Game Engine Algorithm Competition
        await game_engine_algorithm_competition()
        
        # 2. Distributed Web Scraper
        await distributed_web_scraper()
        
        # 3. Microservices Architecture
        await microservices_architecture()
        
        # 4. Machine Learning Pipeline
        await machine_learning_pipeline()
        
    except Exception as e:
        print(f"Error in advanced examples: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ All advanced examples completed!")
    print("Check ./tmp/ for all generated files")


if __name__ == "__main__":
    asyncio.run(main())