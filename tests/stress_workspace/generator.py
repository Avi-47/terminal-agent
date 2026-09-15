
import random
import sys

seed = int(sys.stdin.read())
random.seed(seed)

numbers = [
    random.randint(-100, 100)
    for _ in range(10)
]

print(*numbers)
