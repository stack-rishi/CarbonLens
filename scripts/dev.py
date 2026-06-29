import subprocess
import sys
import os
import time

def run_backend():
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.abspath('.')
    return subprocess.Popen(
        ['poetry', 'run', 'uvicorn', 'backend.main:app', 
         '--reload', '--host', '127.0.0.1', '--port', '8080'],
        cwd='backend',
        env=env
    )

def run_frontend():
    return subprocess.Popen(
        ['npm', 'run', 'dev'],
        cwd='frontend',
        shell=sys.platform == 'win32'
    )

def main():
    print("🌿 Starting CarbonLens...")
    print("   Backend → http://localhost:8080")
    print("   Frontend → http://localhost:5173")
    print("   API Docs → http://localhost:8080/docs")
    print("   Press Ctrl+C to stop\n")
    
    backend = run_backend()
    time.sleep(2)
    frontend = run_frontend()
    
    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend.terminate()
        frontend.terminate()
        sys.exit(0)

if __name__ == '__main__':
    main()
