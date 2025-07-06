#!/usr/bin/env python3
"""
Test runner for LeafLoaf LangGraph
"""
import sys
import pytest
import argparse


def main():
    parser = argparse.ArgumentParser(description='Run LeafLoaf tests')
    parser.add_argument('--component', 
                       choices=['agents', 'deepgram', 'voice', 'memory', 'integration', 'all'],
                       default='all',
                       help='Component to test')
    parser.add_argument('--coverage', action='store_true', 
                       help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = []
    
    # Add test directory
    if args.component == 'all':
        pytest_args.append('tests/')
    else:
        pytest_args.append(f'tests/{args.component}/')
    
    # Add coverage
    if args.coverage:
        pytest_args.extend(['--cov=src/', '--cov-report=html'])
    
    # Add verbose
    if args.verbose:
        pytest_args.append('-v')
    
    # Add other useful options
    pytest_args.extend([
        '-s',  # Show print statements
        '--tb=short',  # Short traceback
        '--asyncio-mode=auto'  # Auto async
    ])
    
    print(f"Running tests: pytest {' '.join(pytest_args)}")
    
    # Run pytest
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())