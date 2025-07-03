# AWS Deployment Guide for Todo Application

This guide covers deploying the Todo application to AWS using various services.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Option 1: Deploy with ECS (Elastic Container Service)](#option-1-ecs)
3. [Option 2: Deploy with Elastic Beanstalk](#option-2-elastic-beanstalk)
4. [Option 3: Deploy with EC2](#option-3-ec2)
5. [Database Setup with RDS](#database-setup)
6. [Domain and SSL Setup](#domain-and-ssl)
7. [Monitoring and Logging](#monitoring)

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Docker installed locally
- Domain name (optional)

## Option 1: Deploy with ECS <a name="option-1-ecs"></a>

### 1. Push Docker Images to ECR

```bash
# Create ECR repositories
aws ecr create-repository --repository-name todo-backend --region us-east-1
aws ecr create-repository --repository-name todo-frontend --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [YOUR-ACCOUNT-ID].dkr.ecr.us-east-1.amazonaws.com

# Build and tag images
docker build -t todo-backend ./backend
docker build -t todo-frontend ./frontend

docker tag todo-backend:latest [YOUR-ACCOUNT-ID].dkr.ecr.us-east-1.amazonaws.com/todo-backend:latest
docker tag todo-frontend:latest [YOUR-ACCOUNT-ID].dkr.ecr.us-east-1.amazonaws.com/todo-frontend:latest

# Push images
docker push [YOUR-ACCOUNT-ID].dkr.ecr.us-east-1.amazonaws.com/todo-backend:latest
docker push [YOUR-ACCOUNT-ID].dkr.ecr.us-east-1.amazonaws.com/todo-frontend:latest
```

### 2. Create ECS Task Definitions

Create `backend-task-definition.json`:

```json
{
  "family": "todo-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "todo-backend",
      "image": "[YOUR-ACCOUNT-ID].dkr.ecr.us-east-1.amazonaws.com/todo-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://username:password@rds-endpoint:5432/tododb"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/todo-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Create `frontend-task-definition.json`:

```json
{
  "family": "todo-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "todo-frontend",
      "image": "[YOUR-ACCOUNT-ID].dkr.ecr.us-east-1.amazonaws.com/todo-frontend:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/todo-frontend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 3. Create ECS Cluster and Services

```bash
# Create cluster
aws ecs create-cluster --cluster-name todo-cluster

# Register task definitions
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json
aws ecs register-task-definition --cli-input-json file://frontend-task-definition.json

# Create services (requires VPC, subnets, and security groups)
aws ecs create-service \
  --cluster todo-cluster \
  --service-name todo-backend \
  --task-definition todo-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx]}"

aws ecs create-service \
  --cluster todo-cluster \
  --service-name todo-frontend \
  --task-definition todo-frontend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx]}"
```

### 4. Setup Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name todo-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx

# Create target groups
aws elbv2 create-target-group \
  --name todo-backend-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --target-type ip

aws elbv2 create-target-group \
  --name todo-frontend-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-xxx \
  --target-type ip

# Create listeners and rules
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

## Option 2: Deploy with Elastic Beanstalk <a name="option-2-elastic-beanstalk"></a>

### 1. Create Elastic Beanstalk Application

Create `.ebextensions/01_python.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: main:app
  aws:elasticbeanstalk:application:environment:
    DATABASE_URL: "postgresql://username:password@rds-endpoint:5432/tododb"
```

Create `Procfile`:

```
web: uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Deploy with EB CLI

```bash
# Install EB CLI
pip install awsebcli

# Initialize EB application
eb init -p python-3.11 todo-app

# Create environment
eb create todo-env

# Deploy
eb deploy
```

## Option 3: Deploy with EC2 <a name="option-3-ec2"></a>

### 1. Launch EC2 Instance

```bash
# Launch instance
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxx \
  --subnet-id subnet-xxx
```

### 2. Setup Instance

SSH into the instance and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone your repository
git clone https://github.com/yourusername/todo-app.git
cd todo-app

# Setup environment variables
echo "DATABASE_URL=postgresql://username:password@rds-endpoint:5432/tododb" > .env

# Run with docker-compose
sudo docker-compose up -d
```

## Database Setup with RDS <a name="database-setup"></a>

### 1. Create RDS PostgreSQL Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier todo-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username todouser \
  --master-user-password todopass123 \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxx \
  --backup-retention-period 7
```

### 2. Configure Security Groups

Ensure your RDS security group allows inbound traffic from your application instances on port 5432.

## Domain and SSL Setup <a name="domain-and-ssl"></a>

### 1. Route 53 Setup

```bash
# Create hosted zone
aws route53 create-hosted-zone --name yourdomain.com --caller-reference 2023-01-01

# Create A record pointing to ALB
aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch file://change-batch.json
```

### 2. SSL Certificate with ACM

```bash
# Request certificate
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names "*.yourdomain.com" \
  --validation-method DNS

# Add HTTPS listener to ALB
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

## Monitoring and Logging <a name="monitoring"></a>

### 1. CloudWatch Setup

Create CloudWatch dashboards and alarms:

```bash
# Create log groups
aws logs create-log-group --log-group-name /ecs/todo-backend
aws logs create-log-group --log-group-name /ecs/todo-frontend

# Create CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name todo-backend-cpu-high \
  --alarm-description "Alarm when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### 2. Enable X-Ray Tracing

Add X-Ray SDK to your application:

```python
# In your FastAPI app
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware

app.add_middleware(XRayMiddleware, recorder=xray_recorder)
```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Backend
DATABASE_URL=postgresql://username:password@rds-endpoint:5432/tododb
AWS_REGION=us-east-1
SECRET_KEY=your-secret-key

# Frontend (build time)
VITE_API_URL=https://api.yourdomain.com
```

## CI/CD with GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
      
      - name: Build and push images
        run: |
          docker build -t ${{ secrets.ECR_REGISTRY }}/todo-backend:latest ./backend
          docker build -t ${{ secrets.ECR_REGISTRY }}/todo-frontend:latest ./frontend
          docker push ${{ secrets.ECR_REGISTRY }}/todo-backend:latest
          docker push ${{ secrets.ECR_REGISTRY }}/todo-frontend:latest
      
      - name: Update ECS service
        run: |
          aws ecs update-service --cluster todo-cluster --service todo-backend --force-new-deployment
          aws ecs update-service --cluster todo-cluster --service todo-frontend --force-new-deployment
```

## Cost Optimization Tips

1. Use Fargate Spot for non-critical workloads
2. Enable auto-scaling based on CPU/memory metrics
3. Use RDS proxy to reduce database connections
4. Implement caching with ElastiCache
5. Use CloudFront for static assets
6. Set up lifecycle policies for ECR images
7. Use Reserved Instances for predictable workloads

## Security Best Practices

1. Use AWS Secrets Manager for sensitive data
2. Enable VPC Flow Logs
3. Use AWS WAF for web application firewall
4. Enable GuardDuty for threat detection
5. Implement least privilege IAM policies
6. Enable MFA for AWS console access
7. Use AWS Systems Manager for patch management
8. Enable AWS Config for compliance monitoring

## Troubleshooting

### Common Issues:

1. **Container fails to start**: Check CloudWatch logs
2. **Database connection errors**: Verify security groups and RDS endpoint
3. **Load balancer unhealthy targets**: Check health check settings
4. **High costs**: Review CloudWatch cost explorer

### Useful Commands:

```bash
# View ECS service logs
aws logs tail /ecs/todo-backend --follow

# Check ECS service status
aws ecs describe-services --cluster todo-cluster --services todo-backend

# View RDS status
aws rds describe-db-instances --db-instance-identifier todo-db

# Check ALB health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:...
```

## Backup and Disaster Recovery

1. Enable automated RDS backups
2. Create AMI snapshots of EC2 instances
3. Use AWS Backup for centralized backup management
4. Test disaster recovery procedures regularly
5. Document RTO and RPO requirements

## Support

For issues, check:
- AWS Service Health Dashboard
- CloudWatch Logs
- AWS Support Center
- AWS Forums and Documentation
EOF < /dev/null