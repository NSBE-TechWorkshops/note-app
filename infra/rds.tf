resource "random_password" "database" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = "${local.name_prefix}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_parameter_group" "this" {
  name        = "${local.name_prefix}-postgres"
  family      = "postgres16"
  description = "PostgreSQL settings for ${local.name_prefix}"
}

resource "aws_db_instance" "this" {
  identifier              = "${local.name_prefix}-db"
  engine                  = "postgres"
  engine_version          = var.db_engine_version
  instance_class          = var.db_instance_class
  allocated_storage       = 20
  max_allocated_storage   = 50
  storage_type            = "gp3"
  storage_encrypted       = true
  db_name                 = var.db_name
  username                = var.db_username
  password                = random_password.database.result
  port                    = 5432
  multi_az                = false
  publicly_accessible     = false
  skip_final_snapshot     = true
  deletion_protection     = false
  backup_retention_period = var.db_backup_retention_days
  db_subnet_group_name    = aws_db_subnet_group.this.name
  parameter_group_name    = aws_db_parameter_group.this.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  apply_immediately       = true

  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_secretsmanager_secret" "database" {
  name                    = "${local.name_prefix}/database"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    username     = var.db_username
    password     = random_password.database.result
    host         = aws_db_instance.this.address
    port         = aws_db_instance.this.port
    database     = var.db_name
    database_url = "postgresql://${var.db_username}:${urlencode(random_password.database.result)}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.db_name}"
  })
}

resource "aws_secretsmanager_secret" "application" {
  count                   = var.llm_api_key == null ? 0 : 1
  name                    = "${local.name_prefix}/application"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "application" {
  count     = var.llm_api_key == null ? 0 : 1
  secret_id = aws_secretsmanager_secret.application[0].id
  secret_string = jsonencode({
    llm_api_key = var.llm_api_key
  })
}
