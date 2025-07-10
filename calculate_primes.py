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


def calculate_primes(limit):
    """Calculate all prime numbers up to a given limit."""
    primes = []
    for num in range(2, limit + 1):
        if is_prime(num):
            primes.append(num)
    return primes


def sieve_of_eratosthenes(limit):
    """Calculate primes using the Sieve of Eratosthenes algorithm."""
    if limit < 2:
        return []
    
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i*i, limit + 1, i):
                sieve[j] = False
    
    return [num for num, is_prime in enumerate(sieve) if is_prime]


if __name__ == "__main__":
    # Example usage
    limit = 100
    primes_basic = calculate_primes(limit)
    primes_sieve = sieve_of_eratosthenes(limit)
    
    print(f"Prime numbers up to {limit} (basic method):")
    print(primes_basic)
    print(f"\nNumber of primes: {len(primes_basic)}")
    
    print(f"\nPrime numbers up to {limit} (sieve method):")
    print(primes_sieve)
    print(f"Number of primes: {len(primes_sieve)}")
    
    # Verify both methods give same results
    assert primes_basic == primes_sieve, "Methods should produce identical results"
    print("\n✓ Both methods produce identical results")