def is_prime(n):
    """Check if a number is prime."""
    if n <= 1:
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
    # Check if 33 is prime
    number = 33
    result = is_prime(number)
    print(f"Is {number} prime? {result}")
    
    # Show why 33 is not prime
    if not result:
        for i in range(2, number):
            if number % i == 0:
                print(f"{number} = {i} × {number // i}")
                break