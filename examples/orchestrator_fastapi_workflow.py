#!/usr/bin/env python3
"""
Real-world orchestrator example: Building a FastAPI application sequentially.

This demonstrates the CORE PURPOSE of CC Executor:
- Claude Orchestrator manages the workflow
- Fresh Claude instances handle each task
- WebSockets ensure sequential execution
- Each task builds on previous outputs
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from cc_executor.client.client import WebSocketClient

class FastAPIWorkflowOrchestrator:
    """Orchestrate building a FastAPI app with multiple Claude instances."""
    
    def __init__(self):
        self.client = WebSocketClient()
        self.project_dir = Path("/tmp/fastapi_orchestrator_demo")
        self.workflow_log = []
        
    async def setup_project(self):
        """Initialize project directory."""
        self.project_dir.mkdir(exist_ok=True)
        print(f"📁 Project directory: {self.project_dir}")
        
    async def cleanup_project(self):
        """Clean up project directory."""
        if self.project_dir.exists():
            import shutil
            shutil.rmtree(self.project_dir)
            
    def log_step(self, instance: int, task: str, status: str):
        """Log workflow step."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "instance": instance,
            "task": task,
            "status": status
        }
        self.workflow_log.append(entry)
        print(f"\n[Instance #{instance}] {task}: {status}")
        
    async def execute_task(self, instance: int, task: str, command: str):
        """Execute a task simulating a Claude instance."""
        self.log_step(instance, task, "Starting...")
        
        # Show the command that would be sent to Claude
        print(f"  Command: {command[:100]}..." if len(command) > 100 else f"  Command: {command}")
        
        result = await self.client.execute_command(
            command=command,
            metadata={
                "claude_instance": instance,
                "task": task,
                "workflow": "fastapi_build"
            }
        )
        
        if result["success"]:
            self.log_step(instance, task, "✓ Completed")
            return result["output_data"]
        else:
            self.log_step(instance, task, f"✗ Failed: {result.get('error', 'Unknown error')}")
            return None
            
    async def run_workflow(self):
        """Run the complete FastAPI workflow."""
        print("=" * 80)
        print("FASTAPI ORCHESTRATOR WORKFLOW")
        print("Demonstrating sequential Claude instance coordination")
        print("=" * 80)
        
        await self.setup_project()
        
        try:
            # Connect to WebSocket
            await self.client.connect()
            print("✓ Connected to CC Executor WebSocket\n")
            
            # Task 1: Create FastAPI app structure
            print("\n🤖 ORCHESTRATOR: Spawning Claude Instance #1")
            print("Task: Create FastAPI application structure with User model")
            
            task1_output = await self.execute_task(
                instance=1,
                task="Create FastAPI app structure",
                command=f"""mkdir -p {self.project_dir}/app && cd {self.project_dir} && cat > app/__init__.py << 'EOF'
# FastAPI Application
__version__ = "0.1.0"
EOF

cat > app/main.py << 'EOF'
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Orchestrator Demo API")

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = False

@app.get("/")
def read_root():
    return {"message": "Welcome to Orchestrator Demo API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "0.1.0"}
EOF

cat > app/models.py << 'EOF'
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    disabled = Column(Boolean, default=False)
    hashed_password = Column(String)
EOF

echo "✓ Created FastAPI app structure" && ls -la app/"""
            )
            
            if not task1_output:
                print("❌ Task 1 failed!")
                return False
                
            print(f"\nOutput preview: {task1_output[:200]}...")
            print("\n🤖 ORCHESTRATOR: Instance #1 completed. Waiting before next instance...")
            await asyncio.sleep(1)  # Simulate orchestrator processing
            
            # Task 2: Add authentication endpoints
            print("\n🤖 ORCHESTRATOR: Spawning Claude Instance #2")
            print("Task: Add authentication endpoints using models from Instance #1")
            
            task2_output = await self.execute_task(
                instance=2,
                task="Add authentication endpoints",
                command=f"""cd {self.project_dir} && cat > app/auth.py << 'EOF'
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
EOF

# Now update main.py to include auth endpoints
cat >> app/main.py << 'EOF'

from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from .auth import (
    Token, create_access_token, verify_password, 
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Simplified for demo - in real app, check database
    if form_data.username != "testuser" or form_data.password != "testpass":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=User)
async def create_user(user: User):
    # Simplified for demo
    return user
EOF

echo "✓ Added authentication endpoints" && grep -c "@app" app/main.py && echo "endpoints in main.py"
"""
            )
            
            if not task2_output:
                print("❌ Task 2 failed!")
                return False
                
            print(f"\nOutput preview: {task2_output[:200]}...")
            print("\n🤖 ORCHESTRATOR: Instance #2 completed. Waiting before next instance...")
            await asyncio.sleep(1)
            
            # Task 3: Create tests
            print("\n🤖 ORCHESTRATOR: Spawning Claude Instance #3")
            print("Task: Create comprehensive tests for the application")
            
            task3_output = await self.execute_task(
                instance=3,
                task="Create comprehensive tests",
                command=f"""cd {self.project_dir} && mkdir -p tests && cat > tests/test_main.py << 'EOF'
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Orchestrator Demo API"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_user():
    user_data = {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "full_name": "John Doe"
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    assert response.json()["username"] == "johndoe"

def test_login():
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_incorrect():
    response = client.post(
        "/token", 
        data={"username": "wronguser", "password": "wrongpass"}
    )
    assert response.status_code == 401
EOF

cat > requirements.txt << 'EOF'
fastapi
uvicorn
sqlalchemy
passlib
python-jose[cryptography]
python-multipart
pytest
httpx
EOF

echo "✓ Created test suite and requirements" && wc -l tests/test_main.py requirements.txt"""
            )
            
            if not task3_output:
                print("❌ Task 3 failed!")
                return False
                
            print(f"\nOutput preview: {task3_output[:200]}...")
            
            # Final summary
            print("\n" + "=" * 80)
            print("WORKFLOW COMPLETE")
            print("=" * 80)
            
            # Show project structure
            structure_cmd = f"cd {self.project_dir} && find . -type f -name '*.py' -o -name '*.txt' | sort"
            result = await self.client.execute_command(structure_cmd)
            
            if result["success"]:
                print("\n📁 Final Project Structure:")
                print(result["output_data"])
                
            # Show workflow log
            print("\n📊 Workflow Execution Log:")
            for entry in self.workflow_log:
                print(f"  [{entry['timestamp']}] Instance #{entry['instance']}: {entry['task']} - {entry['status']}")
                
            print("\n✅ Successfully demonstrated orchestrator pattern!")
            print("\nKey achievements:")
            print("1. ✓ Sequential execution - each instance waited for previous")
            print("2. ✓ Fresh context - each instance started clean")  
            print("3. ✓ Output sharing - later instances used files from earlier ones")
            print("4. ✓ Complex workflow - built complete FastAPI app step by step")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.client.disconnect()
            await self.cleanup_project()


async def main():
    """Run the FastAPI orchestrator workflow."""
    orchestrator = FastAPIWorkflowOrchestrator()
    success = await orchestrator.run_workflow()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    # Check if server is running
    try:
        test_client = WebSocketClient()
        asyncio.run(test_client.connect())
        asyncio.run(test_client.disconnect())
    except Exception:
        print("❌ WebSocket server is not running!")
        print("Please start the server first:")
        print("  cc-executor server start")
        sys.exit(1)
        
    asyncio.run(main())