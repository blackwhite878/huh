#!/usr/bin/env python
"""
Startup script - Validates environment and launches backend.
Checks all dependencies, environment variables, and configuration before starting.
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def check_python_version():
    """Check Python 3.10+"""
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def check_dependencies():
    """Check if required packages are installed."""
    required = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "httpx",
        "tenacity",
        "aiofiles",
        "PyYAML",
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing.append(package)

    if missing:
        print(f"\n⚠️  Install missing packages:")
        print(f"   pip install {' '.join(missing)}")
        return False

    return True


def check_env_file():
    """Check .env file exists and has API key."""
    env_path = Path(".env")

    if not env_path.exists():
        print("❌ .env file not found")
        print("   Copy .env.example to .env and add your Chutes AI credentials")
        return False

    with open(env_path) as f:
        content = f.read()

    if "your-chutes-ai-key-here" in content or "your_chutes_ai_api_key_here" in content:
        print("⚠️  .env has placeholder API key - update CHUTES_AI_API_KEY")
        return True  # Still proceed for demo_mode

    if "CHUTES_AI_API_KEY=" in content:
        print("✅ .env configured")
        return True

    print("⚠️  .env missing CHUTES_AI_API_KEY")
    return True


def check_config_yaml():
    """Check config.yaml exists."""
    config_path = Path("config.yaml")

    if not config_path.exists():
        print("❌ config.yaml not found")
        return False

    print("✅ config.yaml found")
    return True


def check_mock_data():
    """Verify mock data is loaded."""
    try:
        from mock_data import load_mock_data
        props = load_mock_data()
        print(f"✅ Mock data loaded ({len(props)} properties)")
        return True
    except Exception as e:
        print(f"❌ Mock data error: {e}")
        return False


async def test_llm_connection():
    """Test basic LLM client initialization."""
    try:
        from llm_client import llm_client
        print("✅ LLM client initialized")
        return True
    except Exception as e:
        print(f"⚠️  LLM client warning: {e}")
        return True  # Not critical for demo_mode


def print_startup_info():
    """Print startup information."""
    print("\n" + "="*60)
    print("Property Agent UI - Backend Ready")
    print("="*60)
    print("\n📍 API Endpoints:")
    print("  • Main API: http://localhost:8000")
    print("  • Swagger Docs: http://localhost:8000/docs")
    print("  • ReDoc Docs: http://localhost:8000/redoc")
    print("\n📚 Key Endpoints:")
    print("  • POST /api/v1/init_session - Initialize session")
    print("  • POST /api/v1/chat - Send message")
    print("  • GET /api/v1/search_status/{session_id} - Check search progress")
    print("\n🔄 Pipeline Flow:")
    print("  1. init_session → semantic alignment (async)")
    print("  2. session_ready polling → ready status")
    print("  3. chat → dialogue with conflict detection")
    print("  4. search_status polling → tier classification → weighting → remarks")
    print("  5. reject_single �� accumulate rejections")
    print("  6. reject_all → NPP learning")
    print("  7. resolve_action → new_prompt OR keep_memories")
    print("\n💡 Test with curl:")
    print('  curl -X POST http://localhost:8000/api/v1/init_session \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"budget": 500000, "agent_style": "professional", "target": "condo in Johor Bahru", "identity": "first_time_buyer", "gender": "female"}\'')
    print("\n" + "="*60)


async def main():
    """Run all checks."""
    print("\n🚀 Starting Property Agent UI Backend...\n")

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        (".env File", check_env_file),
        ("config.yaml", check_config_yaml),
        ("Mock Data", check_mock_data),
        ("LLM Client", test_llm_connection),
    ]

    results = []
    for name, check_fn in checks:
        print(f"\n📋 {name}:")
        try:
            if asyncio.iscoroutinefunction(check_fn):
                result = await check_fn()
            else:
                result = check_fn()
            results.append(result)
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"✅ Checks: {passed}/{total} passed")
    print(f"{'='*60}")

    if passed >= total - 1:  # Allow 1 warning
        print_startup_info()
        print("\n🟢 All systems go! Starting uvicorn...\n")

        # Start uvicorn
        subprocess.run(
            [
                sys.executable, "-m", "uvicorn",
                "main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000",
            ]
        )
    else:
        print("\n🔴 Fix the issues above before starting.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Shutdown requested")
        sys.exit(0)

