
import sys

numbers = list(map(int, sys.stdin.read().split()))
total = 0

for number in numbers:
    total += number

print(total)
