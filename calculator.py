try:
    result = 10 / 0
except ZeroDivisionError as e:
    result = f"Error: {e}"
print(result)
