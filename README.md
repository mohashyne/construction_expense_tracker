# Construction Expense Tracker

A comprehensive web application for managing construction projects, tracking expenses, and handling contractor relationships with multi-tenant support and sophisticated user management.

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [User Types & Workflows](#user-types--workflows)
- [Features](#features)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## 🏗️ Overview

The Construction Expense Tracker is a Django-based web application designed to streamline construction project management for companies and individual contractors. It features a sophisticated multi-tenant architecture, role-based access control, and comprehensive expense tracking capabilities.

### Key Benefits
- **Multi-tenant Architecture**: Support for multiple companies and individual users
- **Role-based Access Control**: Granular permissions system for different user roles
- **Expense Tracking**: Detailed project expense management with budget monitoring
- **Contractor Management**: Comprehensive contractor database and relationship tracking
- **Super Owner System**: Centralized administration for system-wide management
- **Billing Integration**: Built-in subscription and payment processing

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONSTRUCTION TRACKER                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ SUPER OWNER │  │  COMPANIES  │  │ INDIVIDUALS │            │
│  │   PORTAL    │  │   PORTAL    │  │   PORTAL    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│          │              │                  │                   │
│          └──────────────┼──────────────────┘                   │
│                         │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 CORE SYSTEM                             │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │   USERS &   │ │ PROJECTS &  │ │ BILLING &   │       │   │
│  │  │ PERMISSIONS │ │  EXPENSES   │ │ PAYMENTS    │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  │                                                         │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │CONTRACTORS &│ │NOTIFICATIONS│ │  REPORTS &  │       │   │
│  │  │RELATIONSHIPS│ │ & MESSAGES  │ │ ANALYTICS   │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     DATABASE LAYER                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PostgreSQL/SQLite - Multi-tenant Data Storage          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 👥 User Types & Workflows

### 1. **Super Owner** (System Administrator)
```
Super Owner Login
       ↓
Super Owner Dashboard
       ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ User Management │Registration Mgmt│System Analytics │
│                 │                 │                 │
│ • View all users│ • Approve/Reject│ • System stats  │
│ • Manage access │   registrations │ • User activity │
│ • Assign roles  │ • Review docs   │ • Company health│
│ • Bulk actions  │ • Send notices  │ • Export data   │
└─────────────────┴─────────────────┴─────────────────┘
```

**Super Owner Capabilities:**
- ✅ System-wide user management
- ✅ Registration request approval/rejection
- ✅ Company oversight and analytics
- ✅ Billing and subscription management
- ✅ System configuration and maintenance
- ✅ Export system data

### 2. **Company Users** (Business Teams)
```
Company User Login
       ↓
Company Dashboard
       ↓
┌─────────────────┬─────────────────┬─────────────────┐
│  PROJECT MGMT   │  EXPENSE TRACK  │ CONTRACTOR MGMT │
│                 │                 │                 │
│ • Create projects│ • Log expenses  │ • Add contractors│
│ • Set budgets   │ • Track costs   │ • Manage rates  │
│ • Monitor status│ • Approve bills │ • Performance   │
│ • Reports       │ • Budget alerts │ • Relationships │
└─────────────────┴─────────────────┴─────────────────┘
                           ↓
                    Role-Based Access
┌─────────────────┬─────────────────┬─────────────────┐
│     ADMIN       │   SUPERVISOR    │  TEAM MEMBER    │
│                 │                 │                 │
│ • Full access   │ • View/approve  │ • Limited access│
│ • User management│ • Reports      │ • Own tasks only│
│ • System config │ • Oversight     │ • Submit expenses│
│ • All permissions│ • Team leads   │ • View projects │
└─────────────────┴─────────────────┴─────────────────┘
```

**Company User Roles:**
- **Company Admin**: Full system access, user management, all permissions
- **Supervisor/Manager**: Project oversight, expense approval, team management  
- **Team Member**: Basic access, expense submission, project viewing

### 3. **Individual Users** (Freelance Contractors)
```
Individual User Login
       ↓
Individual Dashboard
       ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ PROFILE MGMT    │ BILLING ACCESS  │ SIMPLE TRACKING │
│                 │                 │                 │
│ • Personal info │ • View invoices │ • Basic projects│
│ • Skills/rates  │ • Payment hist. │ • Time tracking │
│ • Availability  │ • Subscription  │ • Simple reports│
│ • Portfolio     │ • Billing prefs │ • Contact info  │
└─────────────────┴─────────────────┴─────────────────┘
```

**Individual User Features:**
- ✅ Personal profile management
- ✅ Basic project tracking
- ✅ Billing and payment access
- ✅ Subscription management
- ✅ Simple reporting tools

## ✨ Features

### Core Functionality
- **Multi-tenant Architecture**: Separate data spaces for companies and individuals
- **Role-based Access Control**: Granular permissions system
- **Project Management**: Comprehensive project tracking with budgets and timelines
- **Expense Management**: Detailed expense tracking with approval workflows
- **Contractor Database**: Complete contractor management system
- **Billing Integration**: Subscription-based billing with multiple payment options

### Security Features
- **Authentication**: Multi-factor authentication support
- **Authorization**: Role-based permission system
- **Data Isolation**: Tenant-specific data segregation
- **Audit Logs**: Comprehensive activity logging
- **Document Security**: Secure file upload and management

### Administrative Tools
- **Super Owner Dashboard**: System-wide administration interface
- **Registration Management**: Approval workflow for new users
- **Analytics & Reporting**: Comprehensive system analytics
- **Billing Management**: Subscription and payment oversight
- **System Monitoring**: Performance and health monitoring

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Node.js 14+ (for frontend assets)
- PostgreSQL 12+ (recommended) or SQLite (development)
- Redis (for caching and sessions)

### Quick Start

1. **Clone the Repository**
```bash
git clone <repository-url>
cd construction_expense_tracker
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Setup**
```bash
cp .env.example .env
# Edit .env with your database and configuration settings
```

5. **Database Setup**
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

6. **Create Super Owner**
```bash
python manage.py create_super_owner --username admin --email admin@example.com
```

7. **Run Development Server**
```bash
python manage.py runserver
```

8. **Access the Application**
- Application: http://localhost:8000
- Super Owner Dashboard: http://localhost:8000/super-owner/
- Admin Interface: http://localhost:8000/admin/

## 📖 Usage Guide

### For Super Owners

1. **Initial Setup**
   - Log in to super owner dashboard
   - Review system settings
   - Configure notification templates
   - Set up billing plans

2. **User Management**
   - Monitor registration requests
   - Approve/reject new companies and individuals
   - Manage system-wide user access
   - Review user activity and analytics

3. **System Administration**
   - Configure system settings
   - Manage billing and subscriptions
   - Generate system reports
   - Monitor system health

### For Company Administrators

1. **Company Setup**
   - Complete company profile
   - Set up user roles and permissions
   - Configure notification preferences
   - Set up billing information

2. **User Management**
   - Invite team members
   - Assign roles and permissions
   - Manage company memberships
   - Monitor user activity

3. **Project Management**
   - Create and manage projects
   - Set budgets and timelines
   - Track project progress
   - Generate project reports

### For Team Members

1. **Daily Operations**
   - Log project expenses
   - Update project status
   - Submit expense reports
   - View assigned projects

2. **Expense Management**
   - Submit expenses for approval
   - Upload receipts and documentation
   - Track expense status
   - View expense history

### For Individual Users

1. **Profile Management**
   - Complete personal profile
   - Update skills and availability
   - Set hourly rates
   - Upload portfolio items

2. **Simple Tracking**
   - Track basic project information
   - Log work hours
   - Generate simple reports
   - Manage billing information

## 🔧 Development

### Project Structure
```
construction_expense_tracker/
├── core/                 # Core application (users, auth, admin)
├── dashboard/           # Main dashboard views
├── projects/           # Project management
├── expenses/           # Expense tracking
├── contractors/        # Contractor management  
├── billing/           # Billing and payments
├── templates/         # HTML templates
├── static/           # CSS, JS, images
├── media/           # User uploaded files
└── requirements.txt  # Python dependencies
```

### Key Models

- **User Management**: User, UserProfile, SuperOwner
- **Company System**: Company, CompanyMembership, Role, Permission
- **Project Tracking**: Project, ProjectMember
- **Expense Management**: Expense, ExpenseCategory, ExpenseApproval
- **Contractor System**: Contractor, ContractorRating
- **Billing System**: SubscriptionPlan, UserSubscription, Payment

### Development Commands

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations  
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test

# Debug user issues
python manage.py debug_user_login --username <username>

# Clear sessions
python manage.py clear_sessions --all
```

## 🔍 Troubleshooting

### Common Issues

1. **Super Owner Redirect Loops**
   ```bash
   python manage.py clear_sessions --all
   # Then clear browser cache and cookies
   ```

2. **404 Errors in Admin**
   - Check URL patterns in admin.py
   - Verify model registration
   - Clear browser cache

3. **Permission Denied Errors**
   - Verify user roles and permissions
   - Check middleware configuration
   - Review access control settings

4. **Database Issues**
   ```bash
   python manage.py migrate --fake-initial
   python manage.py migrate
   ```

5. **Static Files Not Loading**
   ```bash
   python manage.py collectstatic --clear
   python manage.py collectstatic
   ```

### Debug Tools

- **Session Debug**: `/super-owner/debug/session/` - Check login and session status
- **Permission Debug**: Use management commands to verify user permissions
- **Log Analysis**: Check Django logs for detailed error information

### Support

For technical support or questions:
1. Check the troubleshooting section above
2. Review Django logs for error details
3. Use the built-in debug tools
4. Create an issue in the project repository

## 📊 System Health Monitoring

The application includes built-in monitoring for:
- User activity and engagement
- System performance metrics  
- Database health and optimization
- Error tracking and reporting
- Billing and subscription status

## 🔒 Security Considerations

- Regular security updates and patches
- Secure file upload handling
- SQL injection prevention
- XSS protection
- CSRF protection
- Secure session management
- Role-based access control
- Data encryption at rest and in transit

---

**Construction Expense Tracker** - Built with Django, designed for scalability and ease of use.
