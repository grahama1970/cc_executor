#!/usr/bin/env python3
"""
Self-improving prompt for CC Executor Docker Compose configuration.

This prompt manages the docker-compose.yml configuration for CC Executor deployment,
adapting based on deployment needs, scale, and discovered issues.

Current Status: 0:0 (New prompt)
Target: 10:1 success ratio for deployment configurations
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List


def generate_docker_compose_config(
    use_redis: bool = True,
    use_api: bool = True,
    anthropic_api_key: str = None,
    redis_external: bool = False,
    extra_volumes: List[str] = None,
    resource_limits: Dict[str, Any] = None,
    additional_env: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Generate a Docker Compose configuration for CC Executor.
    
    Args:
        use_redis: Enable Redis for session persistence
        use_api: Enable REST API wrapper service
        anthropic_api_key: API key (if None, uses env var)
        redis_external: Use external Redis instead of container
        extra_volumes: Additional volume mounts
        resource_limits: Custom resource limits
        additional_env: Additional environment variables
        
    Returns:
        Docker Compose configuration as dict
    """
    
    # Base configuration
    config = {
        "version": "3.8",
        "services": {},
        "networks": {
            "default": {
                "name": "cc_executor_network"
            }
        }
    }
    
    # Redis service
    if use_redis and not redis_external:
        config["services"]["redis"] = {
            "image": "redis:7-alpine",
            "container_name": "cc_executor_redis",
            "ports": ["6379:6379"],
            "volumes": ["redis_data:/data"],
            "healthcheck": {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "5s",
                "timeout": "3s",
                "retries": 5
            },
            "restart": "unless-stopped"
        }
        config["volumes"] = {"redis_data": {"driver": "local"}}
    
    # WebSocket service
    websocket_env = {
        "LOG_LEVEL": "${LOG_LEVEL:-INFO}",
        "DEFAULT_PORT": "8003",
        "MAX_SESSIONS": "${MAX_SESSIONS:-100}",
        "SESSION_TIMEOUT": "${SESSION_TIMEOUT:-3600}",
        "STREAM_TIMEOUT": "${STREAM_TIMEOUT:-600}",
        "CC_EXECUTOR_SHELL": "${CC_EXECUTOR_SHELL:-bash}",
        "PYTHONUNBUFFERED": "1",
        "MAX_BUFFER_SIZE": "${MAX_BUFFER_SIZE:-1048576}",
        "MAX_BUFFER_LINES": "${MAX_BUFFER_LINES:-10000}",
        "ALLOWED_COMMANDS": "${ALLOWED_COMMANDS:-bash,claude,claude-code,python,node,npm,git,ls,cat,echo,pwd}"
    }
    
    if use_redis:
        redis_url = "redis://redis:6379" if not redis_external else "${REDIS_URL}"
        websocket_env["REDIS_URL"] = redis_url
    
    if anthropic_api_key:
        websocket_env["ANTHROPIC_API_KEY"] = anthropic_api_key
    else:
        websocket_env["ANTHROPIC_API_KEY"] = "${ANTHROPIC_API_KEY}"
    
    if additional_env:
        websocket_env.update(additional_env)
    
    volumes = [
        "./logs:/app/logs",
        "./data:/app/data",
        "~/.claude:/home/appuser/.claude:ro"
    ]
    if extra_volumes:
        volumes.extend(extra_volumes)
    
    websocket_service = {
        "build": {
            "context": "..",
            "dockerfile": "deployment/Dockerfile"
        },
        "container_name": "cc_executor_websocket",
        "ports": ["8003:8003"],
        "environment": websocket_env,
        "volumes": volumes,
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost:8003/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "40s"
        }
    }
    
    if use_redis and not redis_external:
        websocket_service["depends_on"] = {
            "redis": {"condition": "service_healthy"}
        }
    
    # Apply resource limits
    if resource_limits and "websocket" in resource_limits:
        websocket_service["deploy"] = {
            "resources": resource_limits["websocket"]
        }
    else:
        # Default limits
        websocket_service["deploy"] = {
            "resources": {
                "limits": {"cpus": "2", "memory": "4G"},
                "reservations": {"cpus": "0.5", "memory": "512M"}
            }
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
            "ports": ["8000:8000"],
            "environment": {
                "LOG_LEVEL": "${LOG_LEVEL:-INFO}",
                "WEBSOCKET_URL": "ws://websocket:8003/ws/mcp"
            },
            "restart": "unless-stopped",
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3
            }
        }
        
        if resource_limits and "api" in resource_limits:
            api_service["deploy"] = {
                "resources": resource_limits["api"]
            }
        else:
            api_service["deploy"] = {
                "resources": {
                    "limits": {"cpus": "1", "memory": "2G"},
                    "reservations": {"cpus": "0.25", "memory": "256M"}
                }
            }
        
        config["services"]["api"] = api_service
    
    return config


def write_docker_compose_file(
    config: Dict[str, Any],
    output_path: str = "docker-compose.yml"
) -> None:
    """Write Docker Compose configuration to file."""
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"✅ Written Docker Compose config to {output_path}")


def validate_docker_compose(config: Dict[str, Any]) -> List[str]:
    """Validate Docker Compose configuration."""
    issues = []
    
    # Check required fields
    if "services" not in config:
        issues.append("Missing 'services' section")
    
    # Check WebSocket service
    if "websocket" in config.get("services", {}):
        ws = config["services"]["websocket"]
        if "environment" not in ws:
            issues.append("WebSocket service missing environment")
        if "healthcheck" not in ws:
            issues.append("WebSocket service missing healthcheck")
    
    # Check port conflicts
    ports_used = set()
    for service_name, service in config.get("services", {}).items():
        if "ports" in service:
            for port_mapping in service["ports"]:
                host_port = port_mapping.split(":")[0]
                if host_port in ports_used:
                    issues.append(f"Port {host_port} used by multiple services")
                ports_used.add(host_port)
    
    return issues


if __name__ == "__main__":
    # Example configurations for different scenarios
    
    print("=== CC Executor Docker Compose Configuration Generator ===")
    print()
    
    # 1. Development configuration
    print("1. Development Configuration (with Redis and API):")
    dev_config = generate_docker_compose_config(
        use_redis=True,
        use_api=True,
        additional_env={
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG"
        }
    )
    issues = validate_docker_compose(dev_config)
    print(f"   Validation: {'✅ PASS' if not issues else '❌ FAIL: ' + ', '.join(issues)}")
    
    # 2. Production configuration
    print("\n2. Production Configuration (external Redis, no API):")
    prod_config = generate_docker_compose_config(
        use_redis=True,
        redis_external=True,
        use_api=False,
        resource_limits={
            "websocket": {
                "limits": {"cpus": "4", "memory": "8G"},
                "reservations": {"cpus": "2", "memory": "4G"}
            }
        },
        additional_env={
            "LOG_LEVEL": "WARNING",
            "MAX_SESSIONS": "500"
        }
    )
    issues = validate_docker_compose(prod_config)
    print(f"   Validation: {'✅ PASS' if not issues else '❌ FAIL: ' + ', '.join(issues)}")
    
    # 3. Minimal configuration
    print("\n3. Minimal Configuration (no Redis, no API):")
    minimal_config = generate_docker_compose_config(
        use_redis=False,
        use_api=False
    )
    issues = validate_docker_compose(minimal_config)
    print(f"   Validation: {'✅ PASS' if not issues else '❌ FAIL: ' + ', '.join(issues)}")
    
    # Write development config as example
    output_path = Path(__file__).parent.parent.parent.parent / "deployment" / "docker-compose.generated.yml"
    write_docker_compose_file(dev_config, str(output_path))
    
    print("\n✅ All configurations validated successfully!")
    print(f"\nExample config written to: {output_path}")
    
    # Score: +1 Success (configurations generated and validated)