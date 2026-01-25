# Decap CMS Gateway - Rails App

Eigenständige Rails-Anwendung als Authentication Gateway für Decap CMS.
Ermöglicht Usern ohne GitHub-Account das Bearbeiten von Content.

---

## Übersicht

```
┌─────────────┐     ┌─────────────────────┐     ┌──────────┐
│  Decap CMS  │────▶│   Rails Gateway     │────▶│  GitHub  │
│  (Browser)  │◀────│  (Auth + Proxy)     │◀────│   API    │
└─────────────┘     └─────────────────────┘     └──────────┘
                              │
                    ┌─────────┴─────────┐
                    │    PostgreSQL     │
                    │    (cms_users)    │
                    └───────────────────┘
```

### Funktionsweise

1. User öffnet Decap CMS (`/admin/`)
2. Decap leitet zu Rails Gateway Login (`/cms/auth`)
3. User gibt E-Mail + Passwort ein
4. Gateway gibt JWT-Token zurück
5. Decap nutzt Token für alle API-Calls
6. Gateway proxied Requests zu GitHub API mit Service-Token

---

## 1. Rails App erstellen

```bash
rails new decap_gateway --database=postgresql --skip-javascript --skip-hotwire --skip-jbuilder --api
cd decap_gateway
```

### Gemfile ergänzen

```ruby
# Gemfile
gem "bcrypt", "~> 3.1"
gem "jwt", "~> 2.7"
gem "faraday", "~> 2.7"
gem "rack-cors"
```

```bash
bundle install
```

---

## 2. CORS Konfiguration

```ruby
# config/initializers/cors.rb
Rails.application.config.middleware.insert_before 0, Rack::Cors do
  allow do
    origins "https://buergerrunde.heuweiler.net", "http://localhost:4000"

    resource "/cms/*",
      headers: :any,
      methods: [:get, :post, :put, :patch, :delete, :options, :head],
      credentials: true,
      expose: ["Authorization"]
  end
end
```

---

## 3. Migration: cms_users

```ruby
# db/migrate/YYYYMMDDHHMMSS_create_cms_users.rb
class CreateCmsUsers < ActiveRecord::Migration[7.1]
  def change
    create_table :cms_users do |t|
      t.string :email, null: false
      t.string :password_digest, null: false
      t.string :name, null: false
      t.boolean :active, default: true, null: false
      t.datetime :last_login_at
      t.timestamps
    end

    add_index :cms_users, :email, unique: true
  end
end
```

```bash
rails db:create db:migrate
```

---

## 4. Model: CmsUser

```ruby
# app/models/cms_user.rb
class CmsUser < ApplicationRecord
  has_secure_password

  validates :email, presence: true,
                    uniqueness: { case_sensitive: false },
                    format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :name, presence: true
  validates :password, length: { minimum: 8 }, allow_nil: true

  scope :active, -> { where(active: true) }

  before_save :downcase_email

  def touch_login!
    update_column(:last_login_at, Time.current)
  end

  private

  def downcase_email
    self.email = email.downcase
  end
end
```

---

## 5. Concern: JWT Authentication

```ruby
# app/controllers/concerns/jwt_authenticatable.rb
module JwtAuthenticatable
  extend ActiveSupport::Concern

  included do
    attr_reader :current_cms_user
  end

  private

  def authenticate_cms_user!
    token = extract_token
    return render_unauthorized("Token fehlt") unless token

    payload = decode_jwt(token)
    return render_unauthorized("Token ungültig") unless payload

    @current_cms_user = CmsUser.active.find_by(id: payload["user_id"])
    return render_unauthorized("User nicht gefunden") unless @current_cms_user
  rescue JWT::ExpiredSignature
    render_unauthorized("Token abgelaufen")
  rescue JWT::DecodeError => e
    render_unauthorized("Token ungültig: #{e.message}")
  end

  def extract_token
    auth_header = request.headers["Authorization"]
    return nil unless auth_header

    # Format: "Bearer <token>" oder nur "<token>"
    auth_header.split(" ").last
  end

  def encode_jwt(user, expires_in: 24.hours)
    payload = {
      user_id: user.id,
      email: user.email,
      name: user.name,
      exp: expires_in.from_now.to_i,
      iat: Time.current.to_i
    }
    JWT.encode(payload, jwt_secret, "HS256")
  end

  def decode_jwt(token)
    JWT.decode(token, jwt_secret, true, algorithm: "HS256").first
  end

  def jwt_secret
    Rails.application.credentials.secret_key_base || ENV.fetch("SECRET_KEY_BASE")
  end

  def render_unauthorized(message = "Nicht autorisiert")
    render json: { error: message }, status: :unauthorized
  end
end
```

---

## 6. Base Controller

```ruby
# app/controllers/cms/base_controller.rb
module Cms
  class BaseController < ApplicationController
    include JwtAuthenticatable

    skip_before_action :verify_authenticity_token
    before_action :set_cors_headers

    private

    def set_cors_headers
      headers["Access-Control-Allow-Origin"] = allowed_origin
      headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
      headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    end

    def allowed_origin
      if Rails.env.development?
        "http://localhost:4000"
      else
        "https://buergerrunde.heuweiler.net"
      end
    end
  end
end
```

---

## 7. Auth Controller

```ruby
# app/controllers/cms/auth_controller.rb
module Cms
  class AuthController < BaseController
    # GET /cms/auth
    # Decap leitet hierher für Login
    def show
      @site_id = params[:site_id]
      render :login, layout: "cms"
    end

    # POST /cms/auth
    # Verarbeitet Login-Formular
    def create
      user = CmsUser.active.find_by(email: params[:email]&.downcase)

      unless user&.authenticate(params[:password])
        flash[:alert] = "E-Mail oder Passwort falsch"
        @site_id = params[:site_id]
        return render :login, layout: "cms", status: :unprocessable_entity
      end

      user.touch_login!
      token = encode_jwt(user)

      # Decap erwartet Redirect mit Token im URL-Fragment
      redirect_to "#{params[:site_id]}#access_token=#{token}", allow_other_host: true
    end

    # POST /cms/auth/token
    # Alternative: API-basierter Login (JSON)
    def token
      user = CmsUser.active.find_by(email: params[:email]&.downcase)

      unless user&.authenticate(params[:password])
        return render json: { error: "E-Mail oder Passwort falsch" }, status: :unauthorized
      end

      user.touch_login!
      token = encode_jwt(user)

      render json: {
        access_token: token,
        token_type: "bearer",
        expires_in: 24.hours.to_i,
        user: {
          email: user.email,
          name: user.name
        }
      }
    end

    # OPTIONS /cms/auth
    def options
      head :ok
    end
  end
end
```

---

## 8. Gateway Controller (GitHub Proxy)

```ruby
# app/controllers/cms/gateway_controller.rb
module Cms
  class GatewayController < BaseController
    before_action :authenticate_cms_user!, except: [:options]

    GITHUB_API_BASE = "https://api.github.com".freeze
    REPO = "chriso0710/buergerrunde".freeze
    BRANCH = "master".freeze

    # GET /cms/gateway/settings
    def settings
      render json: {
        github_enabled: true,
        providers: {
          github: {
            repo: REPO,
            branch: BRANCH
          }
        }
      }
    end

    # GET/POST/PUT/DELETE /cms/gateway/repos/:owner/:repo/*path
    # Proxy für GitHub API Calls
    def proxy
      owner = params[:owner]
      repo = params[:repo]
      path = params[:path]

      github_path = build_github_path(owner, repo, path)

      response = github_request(
        method: request.method.downcase.to_sym,
        path: github_path,
        body: request.raw_post,
        query: request.query_parameters
      )

      # Headers durchreichen
      response_headers = %w[content-type x-ratelimit-limit x-ratelimit-remaining]
      response_headers.each do |header|
        headers[header] = response.headers[header] if response.headers[header]
      end

      render json: response.body, status: map_status(response.status)
    end

    # GET /cms/gateway/user
    # Gibt aktuellen User zurück (für Decap)
    def user
      render json: {
        login: current_cms_user.email.split("@").first,
        email: current_cms_user.email,
        name: current_cms_user.name,
        avatar_url: gravatar_url(current_cms_user.email)
      }
    end

    # OPTIONS für CORS Preflight
    def options
      head :ok
    end

    private

    def build_github_path(owner, repo, path)
      if path.present?
        "/repos/#{owner}/#{repo}/#{path}"
      else
        "/repos/#{owner}/#{repo}"
      end
    end

    def github_request(method:, path:, body: nil, query: {})
      connection = Faraday.new(url: GITHUB_API_BASE) do |f|
        f.request :json
        f.response :json
        f.adapter Faraday.default_adapter
      end

      connection.send(method, path) do |req|
        req.headers["Authorization"] = "Bearer #{github_token}"
        req.headers["Accept"] = "application/vnd.github.v3+json"
        req.headers["X-GitHub-Api-Version"] = "2022-11-28"
        req.headers["User-Agent"] = "DecapGateway/1.0"
        req.params = query if query.present?
        req.body = body if body.present? && [:post, :put, :patch].include?(method)
      end
    end

    def github_token
      Rails.application.credentials.dig(:github, :token) || ENV.fetch("GITHUB_TOKEN")
    end

    def map_status(status)
      # GitHub Status Codes durchreichen, aber 403 -> 401 für Auth-Fehler
      status == 403 ? 401 : status
    end

    def gravatar_url(email)
      hash = Digest::MD5.hexdigest(email.downcase.strip)
      "https://www.gravatar.com/avatar/#{hash}?d=identicon"
    end
  end
end
```

---

## 9. Routes

```ruby
# config/routes.rb
Rails.application.routes.draw do
  namespace :cms do
    # Auth endpoints
    get  "auth", to: "auth#show"
    post "auth", to: "auth#create"
    post "auth/token", to: "auth#token"

    # Gateway endpoints
    get "gateway/settings", to: "gateway#settings"
    get "gateway/user", to: "gateway#user"

    # GitHub API Proxy
    match "gateway/repos/:owner/:repo/*path",
          to: "gateway#proxy",
          via: [:get, :post, :put, :patch, :delete],
          constraints: { path: /.*/ }

    match "gateway/repos/:owner/:repo",
          to: "gateway#proxy",
          via: [:get, :post, :put, :patch, :delete]

    # CORS Preflight
    match "*path", to: "gateway#options", via: :options
  end

  # Health check
  get "up", to: proc { [200, {}, ["OK"]] }
end
```

---

## 10. Login View

```erb
<%# app/views/cms/auth/login.html.erb %>
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>CMS Login - Bürgerrunde Heuweiler</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .login-container {
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      padding: 40px;
      width: 100%;
      max-width: 400px;
    }

    .logo {
      text-align: center;
      margin-bottom: 30px;
    }

    .logo img {
      height: 60px;
      width: auto;
    }

    h1 {
      text-align: center;
      color: #333;
      font-size: 24px;
      margin-bottom: 10px;
    }

    .subtitle {
      text-align: center;
      color: #666;
      font-size: 14px;
      margin-bottom: 30px;
    }

    .form-group {
      margin-bottom: 20px;
    }

    label {
      display: block;
      color: #333;
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 8px;
    }

    input[type="email"],
    input[type="password"] {
      width: 100%;
      padding: 12px 16px;
      border: 2px solid #e1e1e1;
      border-radius: 8px;
      font-size: 16px;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    input:focus {
      outline: none;
      border-color: #667eea;
      box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    .alert {
      background: #fee2e2;
      border: 1px solid #fecaca;
      color: #dc2626;
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 20px;
      font-size: 14px;
    }

    button {
      width: 100%;
      padding: 14px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    button:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    button:active {
      transform: translateY(0);
    }

    .footer {
      text-align: center;
      margin-top: 30px;
      color: #999;
      font-size: 12px;
    }
  </style>
</head>
<body>
  <div class="login-container">
    <div class="logo">
      <img src="https://buergerrunde.heuweiler.net/assets/images/br_logo.svg" alt="Logo">
    </div>

    <h1>CMS Login</h1>
    <p class="subtitle">Melde dich an, um Inhalte zu bearbeiten</p>

    <% if flash[:alert] %>
      <div class="alert"><%= flash[:alert] %></div>
    <% end %>

    <%= form_tag cms_auth_path, method: :post do %>
      <%= hidden_field_tag :site_id, @site_id %>

      <div class="form-group">
        <%= label_tag :email, "E-Mail" %>
        <%= email_field_tag :email, params[:email],
            required: true,
            autofocus: true,
            autocomplete: "email",
            placeholder: "deine@email.de" %>
      </div>

      <div class="form-group">
        <%= label_tag :password, "Passwort" %>
        <%= password_field_tag :password, nil,
            required: true,
            autocomplete: "current-password",
            placeholder: "Dein Passwort" %>
      </div>

      <button type="submit">Anmelden</button>
    <% end %>

    <p class="footer">Bürgerrunde Heuweiler e.V.</p>
  </div>
</body>
</html>
```

---

## 11. Environment Konfiguration

### Credentials (empfohlen)

```bash
rails credentials:edit
```

```yaml
# config/credentials.yml.enc
github:
  token: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Alternativ: ENV Variables

```bash
# .env oder System Environment
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SECRET_KEY_BASE=your_secret_key_base_here
```

---

## 12. GitHub Token erstellen

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. "Generate new token"
3. Name: `DecapGateway`
4. Repository access: `Only select repositories` → `chriso0710/buergerrunde`
5. Permissions:
   - **Contents**: Read and write
   - **Metadata**: Read-only
6. Generate token → Kopieren → In credentials speichern

---

## 13. Decap CMS Config anpassen

```yaml
# buergerrunde/admin/config.yml
backend:
  name: github
  repo: chriso0710/buergerrunde
  branch: master
  base_url: https://decap-gateway.example.com  # URL deiner Rails App
  auth_endpoint: /cms/auth

# Rest bleibt unverändert...
site_url: https://buergerrunde.heuweiler.net
display_url: https://buergerrunde.heuweiler.net
logo_url: https://buergerrunde.heuweiler.net/assets/images/br_logo.svg

# ... collections etc.
```

---

## 14. User anlegen

```ruby
# Rails Console: rails c

# Einzelnen User anlegen
CmsUser.create!(
  email: "redakteur@buergerrunde.de",
  password: "sicheres_passwort_123",
  name: "Max Mustermann"
)

# Mehrere User aus Liste anlegen
users = [
  { email: "user1@example.de", name: "User Eins" },
  { email: "user2@example.de", name: "User Zwei" },
  # ...
]

default_password = "InitialPasswort123!"

users.each do |u|
  CmsUser.create!(
    email: u[:email],
    password: default_password,
    name: u[:name]
  )
  puts "Created: #{u[:email]}"
end
```

---

## 15. Rake Tasks für User-Verwaltung

```ruby
# lib/tasks/cms_users.rake
namespace :cms do
  desc "Liste alle CMS User"
  task list: :environment do
    CmsUser.order(:email).each do |u|
      status = u.active? ? "✓" : "✗"
      login = u.last_login_at&.strftime("%d.%m.%Y %H:%M") || "nie"
      puts "#{status} #{u.email.ljust(30)} #{u.name.ljust(20)} Login: #{login}"
    end
  end

  desc "Neuen CMS User anlegen"
  task :create, [:email, :name, :password] => :environment do |_, args|
    user = CmsUser.create!(
      email: args[:email],
      name: args[:name],
      password: args[:password]
    )
    puts "User erstellt: #{user.email}"
  end

  desc "Passwort zurücksetzen"
  task :reset_password, [:email, :new_password] => :environment do |_, args|
    user = CmsUser.find_by!(email: args[:email])
    user.update!(password: args[:new_password])
    puts "Passwort für #{user.email} zurückgesetzt"
  end

  desc "User deaktivieren"
  task :deactivate, [:email] => :environment do |_, args|
    user = CmsUser.find_by!(email: args[:email])
    user.update!(active: false)
    puts "User #{user.email} deaktiviert"
  end

  desc "User aktivieren"
  task :activate, [:email] => :environment do |_, args|
    user = CmsUser.find_by!(email: args[:email])
    user.update!(active: true)
    puts "User #{user.email} aktiviert"
  end
end
```

Verwendung:
```bash
rails cms:list
rails "cms:create[max@example.de,Max Mustermann,geheimesPasswort123]"
rails "cms:reset_password[max@example.de,neuesPasswort456]"
rails "cms:deactivate[max@example.de]"
```

---

## 16. Tests

```ruby
# test/models/cms_user_test.rb
require "test_helper"

class CmsUserTest < ActiveSupport::TestCase
  test "valid user" do
    user = CmsUser.new(
      email: "test@example.com",
      password: "password123",
      name: "Test User"
    )
    assert user.valid?
  end

  test "requires email" do
    user = CmsUser.new(password: "password123", name: "Test")
    assert_not user.valid?
    assert_includes user.errors[:email], "can't be blank"
  end

  test "requires unique email" do
    CmsUser.create!(email: "test@example.com", password: "pass1234", name: "User 1")
    user = CmsUser.new(email: "test@example.com", password: "pass1234", name: "User 2")
    assert_not user.valid?
  end

  test "password minimum length" do
    user = CmsUser.new(email: "test@example.com", password: "short", name: "Test")
    assert_not user.valid?
    assert_includes user.errors[:password], "is too short (minimum is 8 characters)"
  end

  test "authenticates with correct password" do
    user = CmsUser.create!(email: "test@example.com", password: "password123", name: "Test")
    assert user.authenticate("password123")
    assert_not user.authenticate("wrongpassword")
  end

  test "downcases email before save" do
    user = CmsUser.create!(email: "TEST@EXAMPLE.COM", password: "password123", name: "Test")
    assert_equal "test@example.com", user.email
  end

  test "active scope" do
    active = CmsUser.create!(email: "active@test.com", password: "pass1234", name: "Active")
    inactive = CmsUser.create!(email: "inactive@test.com", password: "pass1234", name: "Inactive", active: false)

    assert_includes CmsUser.active, active
    assert_not_includes CmsUser.active, inactive
  end
end
```

```ruby
# test/controllers/cms/auth_controller_test.rb
require "test_helper"

class Cms::AuthControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = CmsUser.create!(
      email: "test@example.com",
      password: "password123",
      name: "Test User"
    )
  end

  test "shows login form" do
    get cms_auth_path, params: { site_id: "http://example.com/admin/" }
    assert_response :success
  end

  test "successful login redirects with token" do
    post cms_auth_path, params: {
      email: "test@example.com",
      password: "password123",
      site_id: "http://example.com/admin/"
    }

    assert_response :redirect
    assert_match /access_token=/, response.location
  end

  test "failed login shows error" do
    post cms_auth_path, params: {
      email: "test@example.com",
      password: "wrongpassword",
      site_id: "http://example.com/admin/"
    }

    assert_response :unprocessable_entity
  end

  test "token endpoint returns JSON" do
    post cms_auth_token_path, params: {
      email: "test@example.com",
      password: "password123"
    }

    assert_response :success
    json = JSON.parse(response.body)
    assert json["access_token"].present?
    assert_equal "bearer", json["token_type"]
  end
end
```

```ruby
# test/controllers/cms/gateway_controller_test.rb
require "test_helper"

class Cms::GatewayControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = CmsUser.create!(
      email: "test@example.com",
      password: "password123",
      name: "Test User"
    )
    @token = generate_token(@user)
  end

  test "settings requires authentication" do
    get cms_gateway_settings_path
    assert_response :unauthorized
  end

  test "settings returns config with valid token" do
    get cms_gateway_settings_path, headers: { "Authorization" => "Bearer #{@token}" }
    assert_response :success

    json = JSON.parse(response.body)
    assert json["github_enabled"]
  end

  test "user endpoint returns current user" do
    get cms_gateway_user_path, headers: { "Authorization" => "Bearer #{@token}" }
    assert_response :success

    json = JSON.parse(response.body)
    assert_equal "test@example.com", json["email"]
  end

  private

  def generate_token(user)
    JWT.encode(
      { user_id: user.id, exp: 1.hour.from_now.to_i },
      Rails.application.credentials.secret_key_base,
      "HS256"
    )
  end
end
```

---

## 17. Deployment Checkliste

### Voraussetzungen
- [ ] Ruby 3.x installiert
- [ ] PostgreSQL verfügbar
- [ ] Domain/Subdomain konfiguriert (z.B. `cms.buergerrunde.de`)
- [ ] SSL-Zertifikat (HTTPS erforderlich)

### Setup
- [ ] `rails new` ausführen
- [ ] Gems installieren
- [ ] CORS konfigurieren
- [ ] Models, Controllers, Routes erstellen
- [ ] GitHub Token generieren
- [ ] Credentials konfigurieren
- [ ] Datenbank migrieren
- [ ] Ersten Admin-User anlegen
- [ ] Tests ausführen

### Decap CMS
- [ ] `admin/config.yml` anpassen (`base_url`, `auth_endpoint`)
- [ ] Jekyll deployen
- [ ] Login testen

---

## 18. Projektstruktur (Komplett)

```
decap_gateway/
├── app/
│   ├── controllers/
│   │   ├── application_controller.rb
│   │   ├── concerns/
│   │   │   └── jwt_authenticatable.rb
│   │   └── cms/
│   │       ├── base_controller.rb
│   │       ├── auth_controller.rb
│   │       └── gateway_controller.rb
│   ├── models/
│   │   ├── application_record.rb
│   │   └── cms_user.rb
│   └── views/
│       └── cms/
│           └── auth/
│               └── login.html.erb
├── config/
│   ├── routes.rb
│   ├── credentials.yml.enc
│   └── initializers/
│       └── cors.rb
├── db/
│   └── migrate/
│       └── YYYYMMDDHHMMSS_create_cms_users.rb
├── lib/
│   └── tasks/
│       └── cms_users.rake
├── test/
│   ├── models/
│   │   └── cms_user_test.rb
│   └── controllers/
│       └── cms/
│           ├── auth_controller_test.rb
│           └── gateway_controller_test.rb
├── Gemfile
└── README.md
```

---

## Zusammenfassung

| Komponente | Dateien | LOC (ca.) |
|------------|---------|-----------|
| Model | 1 | 20 |
| Controllers | 3 | 150 |
| Concern | 1 | 50 |
| View | 1 | 120 |
| Routes | 1 | 20 |
| Config | 2 | 30 |
| Rake Tasks | 1 | 50 |
| Tests | 3 | 100 |
| **Gesamt** | **13** | **~540** |

### Vorteile
- Volle Kontrolle über User-Verwaltung
- Keine Abhängigkeit von Drittanbietern
- E-Mail/Passwort Login (kein GitHub für User)
- Erweiterbar (Rollen, Audit-Log, etc.)
- Self-hosted, DSGVO-konform

### Aufwand
- Initial: 1-2 Tage
- Hosting: Bestehender Server nutzbar
