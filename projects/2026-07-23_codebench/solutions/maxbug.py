import sys
nums = list(map(int, sys.stdin.readline().split()))
print(min(nums))   # BUG: 本来は max を出すべき(不合格デモ用)
