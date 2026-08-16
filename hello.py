"""A simple greeting program."""


def greet(name="World"):
    """Print a greeting message."""
    return f"Hello, {name}!"


def main():
    print(greet())
    print(greet("Python Developer"))


if __name__ == "__main__":
    main()