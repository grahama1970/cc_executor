#!/usr/bin/env python3
"""Generate all prime numbers up to 1000."""

def generate_primes(limit):
    """Generate all prime numbers up to the given limit using the Sieve of Eratosthenes."""
    if limit < 2:
        return []
    
    # Initialize a boolean array "is_prime" and set all entries as true
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False  # 0 and 1 are not prime
    
    # Sieve of Eratosthenes
    p = 2
    while p * p <= limit:
        if is_prime[p]:
            # Mark all multiples of p as not prime
            for i in range(p * p, limit + 1, p):
                is_prime[i] = False
        p += 1
    
    # Collect all prime numbers
    primes = [num for num in range(2, limit + 1) if is_prime[num]]
    return primes

if __name__ == "__main__":
    primes = generate_primes(1000)
    
    print(f"Prime numbers up to 1000 ({len(primes)} total):")
    print("=" * 60)
    
    # Print primes in rows of 10 for readability
    for i in range(0, len(primes), 10):
        row = primes[i:i+10]
        print(" ".join(f"{p:4d}" for p in row))
    
    # Also save to a file
    with open("primes_1000.txt", "w") as f:
        f.write(f"All {len(primes)} prime numbers up to 1000:\n\n")
        for prime in primes:
            f.write(f"{prime}\n")
    
    print(f"\nTotal prime numbers up to 1000: {len(primes)}")
    print("Results also saved to 'primes_1000.txt'")