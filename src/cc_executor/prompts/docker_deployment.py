#!/usr/bin/env python3
"""
Self-improving prompt for Docker deployment configuration.

This prompt manages Docker Compose configurations for CC Executor deployment,
adapting to different environments and requirements.
"""

import os
import yaml
import json
from typing import Dict, Any, List, Optional
from pathlib import Path


def generate_docker_compose_config(
    use_redis: bool = True,
    use_api: bool = True,
    redis_external_port: int = 6380,
    websocket_external_port: int = 8003,
    api_external_port: int = 8001,
    claude_auth_volume: str = "~/.claude",
    log_volume: str = "./logs",
    data_volume: str = "./data",
    resource_limits: Optional[Dict[str, Any]] = None,
    additional_env: Optional[Dict[str, str]] = None,
    network_name: str = "cc_executor_network",
    enable_healthchecks: bool = True,
    compose_version: str = "3.8"
) -> Dict[str, Any]:
    """
    Generate Docker Compose configuration for CC Executor.
    
    Args:
        use_redis: Whether to include Redis service
        use_api: Whether to include FastAPI service
        redis_external_port: External port for Redis (default: 6380 to avoid conflicts)
        websocket_external_port: External port for WebSocket service
        api_external_port: External port for API service
        claude_auth_volume: Volume path for Claude authentication data
        log_volume: Volume path for logs
        data_volume: Volume path for persistent data
        resource_limits: Optional resource limits for containers
        additional_env: Additional environment variables
        network_name: Docker network name
        enable_healthchecks: Whether to enable health checks
        compose_version: Docker Compose version
    
    Returns:
        Docker Compose configuration as a dictionary
    """
    
    # Base configuration
    config = {
        "version": compose_version,
        "services": {},
        "networks": {
            "default": {
                "name": network_name
            }
        }
    }
    
    # Redis service
    if use_redis:
        redis_service = {
            "image": "redis:7-alpine",
            "container_name": "cc_executor_redis",
            "ports": [f"{redis_external_port}:6379"],
            "volumes": ["redis_data:/data"],
            "restart": "unless-stopped"
        }
        
        if enable_healthchecks:
            redis_service["healthcheck"] = {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "5s",
                "timeout": "3s",
                "retries": 5
            }
        
        config["services"]["redis"] = redis_service
        config["volumes"] = {"redis_data": {"driver": "local"}}
    
    # WebSocket service
    websocket_env = {
        "LOG_LEVEL": "INFO",
        "DEFAULT_PORT": "8003",
        "MAX_SESSIONS": "100",
        "SESSION_TIMEOUT": "3600",
        "STREAM_TIMEOUT": "600",
        "CC_EXECUTOR_SHELL": "bash",
        "PYTHONUNBUFFERED": "1",
        "MAX_BUFFER_SIZE": "1048576",
        "MAX_BUFFER_LINES": "10000",
        "ALLOWED_COMMANDS": "bash,claude,claude-code,python,node,npm,git,ls,cat,echo,pwd",
    }
    
    if use_redis:
        websocket_env["REDIS_URL"] = "redis://redis:6379"
    
    if additional_env:
        websocket_env.update(additional_env)
    
    websocket_service = {
        "build": {
            "context": "..",
            "dockerfile": "deployment/Dockerfile"
        },
        "container_name": "cc_executor_websocket",
        "ports": [f"{websocket_external_port}:8003"],
        "environment": websocket_env,
        "volumes": [
            f"{log_volume}:/app/logs",
            f"{data_volume}:/app/data",
            f"{claude_auth_volume}:/home/appuser/.claude"
        ],
        "restart": "unless-stopped"
    }
    
    if use_redis:
        websocket_service["depends_on"] = {
            "redis": {"condition": "service_healthy"}
        }
    
    if enable_healthchecks:
        websocket_service["healthcheck"] = {
            "test": ["CMD", "curl", "-f", "http://localhost:8003/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "40s"
        }
    
    if resource_limits:
        websocket_service["deploy"] = {
            "resources": resource_limits.get("websocket", {
                "limits": {"cpus": "2", "memory": "4G"},
                "reservations": {"cpus": "0.5", "memory": "512M"}
            })
        }
    
    config["services"]["websocket"] = websocket_service
    
    # API service
    if use_api:
        api_service = {
            "build": {
                "context": "..",
                "dockerfile": "deployment/Dockerfile.api"
            },
            "container_name": "cc_executor_api",
            "depends_on": {
                "websocket": {"condition": "service_healthy"}
            },
            "ports": [f"{api_external_port}:8000"],
            "environment": {
                "LOG_LEVEL": "INFO",
                "WEBSOCKET_URL": "ws://websocket:8003/ws"
            },
            "volumes": [
                f"{claude_auth_volume}:/home/apiuser/.claude:ro"
            ],
            "restart": "unless-stopped"
        }
        
        if enable_healthchecks:
            api_service["healthcheck"] = {
                "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3
            }
        
        if resource_limits:
            api_service["deploy"] = {
                "resources": resource_limits.get("api", {
                    "limits": {"cpus": "1", "memory": "2G"},
                    "reservations": {"cpus": "0.25", "memory": "256M"}
                })
            }
        
        config["services"]["api"] = api_service
    
    return config


def generate_env_file(
    anthropic_api_key: Optional[str] = None,
    redis_password: Optional[str] = None,
    additional_vars: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate .env file content for Docker Compose.
    
    Args:
        anthropic_api_key: Optional Anthropic API key (not recommended for web auth)
        redis_password: Optional Redis password
        additional_vars: Additional environment variables
    
    Returns:
        .env file content as string
    """
    env_content = []
    
    if anthropic_api_key:
        env_content.append(f"# ANTHROPIC_API_KEY={anthropic_api_key}")
        env_content.append("# Note: Web authentication is recommended instead of API key")
    
    if redis_password:
        env_content.append(f"REDIS_PASSWORD={redis_password}")
    
    if additional_vars:
        for key, value in additional_vars.items():
            env_content.append(f"{key}={value}")
    
    return "\n".join(env_content)


def generate_deployment_script() -> str:
    """
    Generate deployment script for CC Executor.
    
    Returns:
        Deployment script content
    """
    script = '''#!/bin/bash
# CC Executor Deployment Script
# Generated by self-improving prompt

set -e

echo "CC Executor Docker Deployment"
echo "============================"

# Check Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p logs data claude-config
chmod 755 logs data claude-config

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    touch .env
fi

# Build and start services
echo "Building Docker images..."
docker compose build --no-cache

echo "Starting services..."
docker compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check service status
docker compose ps

# Show authentication instructions
echo ""
echo "Services are running!"
echo ""
echo "To authenticate Claude Code:"
echo "  1. Run: curl -X POST http://localhost:8001/auth/claude"
echo "  2. Follow the authentication URL provided"
echo ""
echo "To test the API:"
echo "  curl http://localhost:8001/health"
echo ""
echo "To view logs:"
echo "  docker compose logs -f"
'''
    return script


def update_docker_compose_file(
    config_updates: Dict[str, Any],
    compose_file_path: str = "docker-compose.yml"
) -> None:
    """
    Update existing Docker Compose file with new configuration.
    
    Args:
        config_updates: Updates to apply to the configuration
        compose_file_path: Path to Docker Compose file
    """
    # Load existing config
    if os.path.exists(compose_file_path):
        with open(compose_file_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = generate_docker_compose_config()
    
    # Apply updates
    def deep_update(base_dict, update_dict):
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    deep_update(config, config_updates)
    
    # Write updated config
    with open(compose_file_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Updated {compose_file_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Docker deployment configuration")
    parser.add_argument("--output", default="docker-compose.yml", help="Output file path")
    parser.add_argument("--no-redis", action="store_true", help="Disable Redis service")
    parser.add_argument("--no-api", action="store_true", help="Disable API service")
    parser.add_argument("--redis-port", type=int, default=6380, help="Redis external port")
    parser.add_argument("--websocket-port", type=int, default=8003, help="WebSocket external port")
    parser.add_argument("--api-port", type=int, default=8001, help="API external port")
    parser.add_argument("--deployment-script", action="store_true", help="Generate deployment script")
    parser.add_argument("--env-file", action="store_true", help="Generate .env file template")
    
    args = parser.parse_args()
    
    if args.deployment_script:
        # Generate deployment script
        script = generate_deployment_script()
        with open("deploy.sh", "w") as f:
            f.write(script)
        os.chmod("deploy.sh", 0o755)
        print("Generated deploy.sh")
    
    elif args.env_file:
        # Generate .env template
        env_content = generate_env_file()
        with open(".env.example", "w") as f:
            f.write(env_content)
        print("Generated .env.example")
    
    else:
        # Generate Docker Compose config
        config = generate_docker_compose_config(
            use_redis=not args.no_redis,
            use_api=not args.no_api,
            redis_external_port=args.redis_port,
            websocket_external_port=args.websocket_port,
            api_external_port=args.api_port
        )
        
        # Write to file
        with open(args.output, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"Generated {args.output}")
        print("\nNext steps:")
        print("1. Create necessary directories: mkdir -p logs data claude-config")
        print("2. Build images: docker compose build")
        print("3. Start services: docker compose up -d")
        print("4. Authenticate Claude: curl -X POST http://localhost:8001/auth/claude")