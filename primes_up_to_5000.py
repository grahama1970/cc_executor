#!/usr/bin/env python3
"""Generate all prime numbers up to 5000 using the Sieve of Eratosthenes algorithm."""

def sieve_of_eratosthenes(limit):
    """Generate all prime numbers up to the given limit using the Sieve of Eratosthenes."""
    if limit < 2:
        return []
    
    # Create a boolean array "is_prime" and initialize all entries as true
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False  # 0 and 1 are not prime
    
    # Start with the smallest prime number, 2
    p = 2
    while p * p <= limit:
        # If is_prime[p] is not changed, then it is a prime
        if is_prime[p]:
            # Mark all multiples of p as not prime
            for i in range(p * p, limit + 1, p):
                is_prime[i] = False
        p += 1
    
    # Collect all prime numbers
    primes = [num for num, prime in enumerate(is_prime) if prime]
    return primes

if __name__ == "__main__":
    # Generate primes up to 5000
    primes = sieve_of_eratosthenes(5000)
    
    # Print the primes
    print(f"Prime numbers up to 5000 ({len(primes)} total):")
    print("=" * 60)
    
    # Print primes in rows of 10 for better readability
    for i in range(0, len(primes), 10):
        row = primes[i:i+10]
        print(" ".join(f"{p:4d}" for p in row))
    
    # Save to file
    with open("primes_5000.txt", "w") as f:
        f.write(f"All prime numbers up to 5000 ({len(primes)} total):\n")
        f.write("=" * 60 + "\n")
        for prime in primes:
            f.write(f"{prime}\n")
    
    print(f"\nResults saved to primes_5000.txt")