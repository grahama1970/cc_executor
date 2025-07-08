def add(a, b): return a + b

if __name__ == "__main__":
    result = add(5, 3)
    print(f"Result: {result}")
    assert result == 8, "Addition failed"