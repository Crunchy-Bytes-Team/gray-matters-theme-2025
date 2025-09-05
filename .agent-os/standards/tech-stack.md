# Tech Stack

> Version: 1.0.0
> Last Updated: 2025-08-31

## Context

This file is part of the Agent OS standards system. These global tech stack defaults are referenced by all product codebases when initializing new projects. Individual projects may override these choices in their `.agent-os/product/tech-stack.md` file.

## Core Technologies

### Application Framework
- **Framework:** Ruby on Rails
- **Version:** 7.0.6
- **Language:** Ruby 3.2.2

### Database
- **Primary:** PostgreSQL
- **Version:** 16+
- **ORM:** Active Record

## Frontend Stack

### JavaScript Framework
- **Framework:** React
- **Version:** Latest stable
- **Build Tool:** Vite

### Import Strategy
- **Strategy:** Node.js modules
- **Package Manager:** yarn
- **jsbundling-rails": 1.3+

### CSS Framework
- **Framework:** TailwindCSS
- **Version:** 4.0+
= **cssbundling-rails:** 1.4+

### Template Engine
- **Engine:** Slim
- **Version:** 5.2+

### Email Templates
- **Engine:** MJML
- **Version:** 4.10+

### Authentication
- **Library:** Devise
- **Version:** 4.9+

### Authorization
- **Library:** Pundit
- **Version:** 2.3+

### Decorators
- **Library:** Draper
- **Version:** 4.0+

## Debugging & Testing
- **pry-rails:** 0.3.9
- **pry-byebug:** 3.10.1
- **pry:** 0.14.2
- **rspec-rails:** 6.1.1
- **rspec:** 3.13.0
- **factory_bot_rails:** 6.4.3
- **capybara:** 3.40.0
- **capybara-screenshot:** 1.0.26
- **selenium-webdriver:** 4.8.0
- **webdrivers:** 5.0.0

### UI Components
- **Library:** Instrumental Components
- **Version:** Latest
- **Installation:** Via development gems group

## Assets & Media

### Fonts
- **Provider:** Google Fonts

### Icons
- **Library:** Lucide
- **Library:** font-awesome

## Infrastructure

### Application Hosting
- **Platform:** Hetzner Cloud
- **Service:** Docker container managed with Coolify

### Database Hosting
- **Provider:** Hetzner Cloud
- **Service:** Docker container PostgreSQL managed with Coolify
- **Backups:** Daily automated

### Asset Storage
- **Provider:** Amazon S3
- **Access:** Private with signed URLs

## Deployment

### CI/CD Pipeline
- **Platform:** GitHub Actions
- **Trigger:** Push to main/staging branches
- **Tests:** Run before deployment

### Environments
- **Production:** main branch
- **Staging:** staging branch
- **Review Apps:** PR-based (optional)

---
