#!/usr/bin/env python3
"""Find all prime numbers between 1 and 1,000,000 using Sieve of Eratosthenes."""

def sieve_of_eratosthenes(limit):
    """Find all prime numbers up to limit using Sieve of Eratosthenes."""
    # Create a boolean array "prime[0..limit]" and initialize all entries as true
    prime = [True] * (limit + 1)
    prime[0] = prime[1] = False  # 0 and 1 are not prime
    
    p = 2
    while p * p <= limit:
        # If prime[p] is not changed, then it is a prime
        if prime[p]:
            # Update all multiples of p
            for i in range(p * p, limit + 1, p):
                prime[i] = False
        p += 1
    
    # Collect all prime numbers
    primes = []
    for i in range(2, limit + 1):
        if prime[i]:
            primes.append(i)
    
    return primes

if __name__ == "__main__":
    print("Calculating all prime numbers between 1 and 1,000,000...")
    primes = sieve_of_eratosthenes(1_000_000)
    
    # Save to file since the list is very long
    with open('primes_1_to_1million.txt', 'w') as f:
        for prime in primes:
            f.write(f"{prime}\n")
    
    print(f"\nTotal number of primes found: {len(primes):,}")
    print(f"First 20 primes: {primes[:20]}")
    print(f"Last 20 primes: {primes[-20:]}")
    print(f"\nAll {len(primes):,} primes have been saved to 'primes_1_to_1million.txt'")