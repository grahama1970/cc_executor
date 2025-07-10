#!/usr/bin/env python3
"""Find the 50th prime number."""

def is_prime(n):
    """Check if a number is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True

def find_nth_prime(n):
    """Find the nth prime number."""
    count = 0
    num = 2
    while count < n:
        if is_prime(num):
            count += 1
            if count == n:
                return num
        num += 1
    return num

if __name__ == "__main__":
    result = find_nth_prime(50)
    print(f"The 50th prime number is: {result}")