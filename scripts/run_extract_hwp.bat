@echo off
REM HWP 추출: Windows에서 python/py 자동 선택. 한글 경로 시 --path-file 사용 권장.
where py >nul 2>nul && py "%~dp0extract_hwp.py" %* || python "%~dp0extract_hwp.py" %*
