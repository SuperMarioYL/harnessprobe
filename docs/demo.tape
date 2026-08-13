Output assets/demo.gif
Set FontSize 16
Set Width 880
Set Height 420
Set Theme "Dracula"
Set Padding 20

# 10-minute happy path: install → match → report → repro
Type "pip install -e ."
Sleep 2s
Enter
Sleep 3s

Type "harnessprobe version"
Sleep 1s
Enter
Sleep 1s

Type "harnessprobe profiles"
Sleep 1s
Enter
Sleep 2s

Type "harnessprobe match --models deepseek-v4,qwen3-8,kimi-k3 --bench aime --n 12"
Sleep 2s
Enter
Sleep 6s

Type "harnessprobe report --html -o report.html"
Sleep 1s
Enter
Sleep 2s

Type "harnessprobe repro --pkg repro-$(date +%s).zip"
Sleep 1s
Enter
Sleep 2s
