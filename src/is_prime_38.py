def is_prime(n):
    """Check if a number is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    # Check odd divisors up to sqrt(n)
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


if __name__ == "__main__":
    number = 38
    result = is_prime(number)
    print(f"Is {number} prime? {result}")
    
    # Show why 38 is not prime
    if not result:
        print(f"{number} = 2 × {number // 2}")