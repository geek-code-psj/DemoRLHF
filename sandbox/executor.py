import subprocess
import tempfile
import os
import json

def run_code(code: str, timeout: int = 15) -> dict:
    """
    Safely execute Python code in a subprocess with a hard timeout.
    Returns stdout, stderr, and exit_code.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ['python', tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            # Restrict environment to bare minimum
            env={
                'PATH': '/usr/local/bin:/usr/bin:/bin',
                'PYTHONDONTWRITEBYTECODE': '1',
            }
        )
        return {
            'stdout': result.stdout[:5000],  # cap output
            'stderr': result.stderr[:5000],
            'exit_code': result.returncode,
            'timed_out': False
        }
    except subprocess.TimeoutExpired:
        return {
            'stdout': '',
            'stderr': f'Execution timed out after {timeout}s',
            'exit_code': -1,
            'timed_out': True
        }
    except Exception as e:
        return {
            'stdout': '',
            'stderr': str(e),
            'exit_code': -2,
            'timed_out': False
        }
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def run_with_tests(code: str, test_code: str, timeout: int = 20) -> dict:
    """
    Write code + test to temp files and run pytest programmatically.
    Returns combined result with pass/fail/error counts.
    """
    import sys
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write the submission code
        code_path = os.path.join(tmpdir, 'submission.py')
        with open(code_path, 'w') as f:
            f.write(code)

        # Write the test file
        test_path = os.path.join(tmpdir, 'test_submission.py')
        with open(test_path, 'w') as f:
            f.write(test_code)

        result_path = os.path.join(tmpdir, 'results.json')

        try:
            proc = subprocess.run(
                [
                    sys.executable, '-m', 'pytest',
                    test_path,
                    '--tb=short',
                    '--no-header',
                    f'--json-report',
                    f'--json-report-file={result_path}',
                    '-q'
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
                env={
                    'PATH': '/usr/local/bin:/usr/bin:/bin',
                    'PYTHONDONTWRITEBYTECODE': '1',
                    'PYTHONPATH': tmpdir,
                }
            )

            # Parse JSON report if available
            if os.path.exists(result_path):
                with open(result_path) as f:
                    report = json.load(f)
                summary = report.get('summary', {})
                return {
                    'stdout': proc.stdout[:5000],
                    'stderr': proc.stderr[:3000],
                    'exit_code': proc.returncode,
                    'tests_passed': summary.get('passed', 0),
                    'tests_failed': summary.get('failed', 0),
                    'tests_error': summary.get('error', 0),
                    'timed_out': False
                }
            else:
                # Fallback: parse from stdout
                passed = proc.stdout.count(' passed')
                failed = proc.stdout.count(' failed')
                return {
                    'stdout': proc.stdout[:5000],
                    'stderr': proc.stderr[:3000],
                    'exit_code': proc.returncode,
                    'tests_passed': 1 if proc.returncode == 0 else 0,
                    'tests_failed': 0 if proc.returncode == 0 else 1,
                    'tests_error': 0,
                    'timed_out': False
                }

        except subprocess.TimeoutExpired:
            return {
                'stdout': '',
                'stderr': f'Test execution timed out after {timeout}s',
                'exit_code': -1,
                'tests_passed': 0,
                'tests_failed': 0,
                'tests_error': 1,
                'timed_out': True
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'exit_code': -2,
                'tests_passed': 0,
                'tests_failed': 0,
                'tests_error': 1,
                'timed_out': False
            }
