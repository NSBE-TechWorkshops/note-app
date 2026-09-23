resource "aws_cognito_user_pool" "this" {
  name                     = local.name_prefix
  auto_verified_attributes = ["email"]

  username_attributes = ["email"]

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_identity_provider" "google" {
  count = var.enable_google_identity_provider ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.this.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
    authorize_scopes = "email profile openid"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
}

resource "aws_cognito_user_pool_client" "this" {
  name         = local.name_prefix
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = false

  supported_identity_providers = var.enable_google_identity_provider ? ["COGNITO", "Google"] : ["COGNITO"]

  callback_urls = var.cognito_callback_urls
  logout_urls   = var.cognito_logout_urls

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  depends_on = [aws_cognito_identity_provider.google]
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = local.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}
