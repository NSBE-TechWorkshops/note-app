resource "aws_ecs_cluster" "backend" {
  name = "${local.name_prefix}-cluster"
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name_prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_cpu
  memory                   = var.ecs_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.container_image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "APP_ENV", value = var.environment },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "S3_BUCKET_NAME", value = aws_s3_bucket.uploads.bucket },
        { name = "COGNITO_USER_POOL_ID", value = aws_cognito_user_pool.this.id },
        { name = "COGNITO_CLIENT_ID", value = aws_cognito_user_pool_client.this.id },
        { name = "COGNITO_ISSUER", value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}" },
        { name = "COGNITO_JWKS_URL", value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}/.well-known/jwks.json" },
        { name = "LLM_PROVIDER", value = var.llm_provider },
        { name = "EMBEDDING_MODEL", value = var.embedding_model },
        { name = "LLM_MODEL", value = var.llm_model },
        { name = "CORS_ORIGINS", value = var.cors_origins },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.document_processor.url },
      ]

      secrets = concat(
        [
          {
            name      = "DATABASE_URL"
            valueFrom = "${aws_secretsmanager_secret.database.arn}:database_url::"
          }
        ],
        var.llm_api_key == null ? [] : [
          {
            name      = "LLM_API_KEY"
            valueFrom = "${aws_secretsmanager_secret.application[0].arn}:llm_api_key::"
          }
        ]
      )

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${var.container_port}${var.health_check_path}')\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 20
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${local.name_prefix}-backend"
  cluster         = aws_ecs_cluster.backend.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.http]
}
