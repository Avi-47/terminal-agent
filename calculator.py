#!/usr/bin/env python3
"""A simple calculator program - fixed version."""


def add(a, b):
    """Add two numbers."""
    return a + b


def multiply(a, b):
    """Multiply two numbers."""
    return a * b


def divide(a, b):
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def greet_user(name):
    """Greet the user by name."""
    message = "Hello, " + name + "!"
    return message


def main():
    """Run the calculator demo."""
    # Basic arithmetic
    result1 = add(10, 5)
    print(f"10 + 5 = {result1}")

    result2 = multiply(4, 3)
    print(f"4 * 3 = {result2}")

    result3 = divide(15, 3)
    print(f"15 / 3 = {result3}")

    # Greeting
    greeting = greet_user("World")
    print(greeting)

    # Fix: compute total_score from the previous results
    total_score = result1 + result2 + result3
    print(f"The final score is: {total_score}")


if __name__ == "__main__":
    main()