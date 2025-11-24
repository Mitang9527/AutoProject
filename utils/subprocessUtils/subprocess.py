import subprocess

from utils.logUtils.logControl import INFO


def execute_python_script(script_path):
    process = None
    try:
        process = subprocess.Popen(
            ['python3', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8'
        )

        for line in iter(process.stdout.readline, ''):
            print(f"STDOUT: {line.strip()}")

        for line in iter(process.stderr.readline, ''):
            print(f"STDERR: {line.strip()}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if process:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
            process.wait()

def run_with_live_output(command):
    process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            INFO.logger.info(f" {line.strip()}")
    return process.returncode
