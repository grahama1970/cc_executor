#!/usr/bin/env python3
"""Generate all prime numbers up to 10,000 using the Sieve of Eratosthenes algorithm."""

def sieve_of_eratosthenes(limit):
    """Generate all prime numbers up to the given limit."""
    # Create a boolean array "is_prime" and initialize all entries as true
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False  # 0 and 1 are not prime
    
    p = 2
    while p * p <= limit:
        # If is_prime[p] is not changed, then it is a prime
        if is_prime[p]:
            # Mark all multiples of p as not prime
            for i in range(p * p, limit + 1, p):
                is_prime[i] = False
        p += 1
    
    # Collect all prime numbers
    primes = [num for num in range(2, limit + 1) if is_prime[num]]
    return primes

if __name__ == "__main__":
    limit = 10000
    primes = sieve_of_eratosthenes(limit)
    
    # Print results
    print(f"Prime numbers up to {limit}:")
    print(f"Total count: {len(primes)}")
    print(f"\nFirst 20 primes: {primes[:20]}")
    print(f"Last 20 primes: {primes[-20:]}")
    
    # Save to file
    with open("primes_10000.txt", "w") as f:
        for prime in primes:
            f.write(f"{prime}\n")
    
    print(f"\nAll {len(primes)} primes saved to primes_10000.txt")