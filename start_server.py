#!/usr/bin/env python
import os
import sys
import subprocess

# Set up environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_tracker.settings')

# Change to project directory
project_dir = '/Users/muhammadibnsalyhu/Desktop/construction_expense_tracker'
os.chdir(project_dir)

def main():
    print("🚀 Starting ConstructPro Development Server...")
    print("=" * 50)
    
    # Kill any existing server on port 8000
    try:
        subprocess.run(['pkill', '-f', 'runserver'], check=False, capture_output=True)
        print("✓ Cleaned up any existing server processes")
    except:
        pass
    
    # Check if migrations are up to date
    print("\n📦 Checking migrations...")
    result = subprocess.run([sys.executable, 'manage.py', 'migrate', '--check'], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print("⚠️  Migrations needed. Running migrations...")
        subprocess.run([sys.executable, 'manage.py', 'migrate'])
    else:
        print("✓ All migrations applied")
    
    # Start the development server
    print("\n🌐 Starting development server...")
    print("📍 Registration URLs available at:")
    print("   • Company Registration: http://127.0.0.1:8000/register/company/")
    print("   • Individual Registration: http://127.0.0.1:8000/register/individual/")
    print("   • Login: http://127.0.0.1:8000/login/")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start server with explicit host and port
    try:
        subprocess.run([
            sys.executable, 'manage.py', 'runserver', 
            '127.0.0.1:8000',
            '--settings=construction_tracker.settings'
        ])
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped successfully")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == '__main__':
    main()
