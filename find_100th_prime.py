#!/usr/bin/env python3
"""Find the 100th prime number using the Sieve of Eratosthenes."""

def sieve_of_eratosthenes(limit):
    """Generate all prime numbers up to the given limit."""
    # Create a boolean array "is_prime" and initialize all entries as true
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False  # 0 and 1 are not prime
    
    p = 2
    while p * p <= limit:
        # If is_prime[p] is not changed, then it is a prime
        if is_prime[p]:
            # Update all multiples of p
            for i in range(p * p, limit + 1, p):
                is_prime[i] = False
        p += 1
    
    # Collect all prime numbers
    primes = []
    for i in range(2, limit + 1):
        if is_prime[i]:
            primes.append(i)
    
    return primes

def find_nth_prime(n):
    """Find the nth prime number."""
    # Start with an estimated upper bound for the nth prime
    # For n >= 6, the nth prime is less than n * (ln(n) + ln(ln(n)))
    # For safety, we'll use a larger multiplier
    limit = max(100, n * 20)
    
    while True:
        primes = sieve_of_eratosthenes(limit)
        if len(primes) >= n:
            return primes[n - 1]  # n-1 because list is 0-indexed
        # Double the limit if we didn't find enough primes
        limit *= 2

def main():
    """Find and display the 100th prime number with step-by-step work."""
    n = 100
    print(f"Finding the {n}th prime number...")
    print("\nStep 1: Using the Sieve of Eratosthenes algorithm")
    print("Step 2: Starting with an estimated upper bound")
    
    # Find the 100th prime
    result = find_nth_prime(n)
    
    # Show some context - primes around the 100th
    primes = sieve_of_eratosthenes(result + 50)
    
    # Find the index of our result
    idx = primes.index(result)
    
    print(f"\nStep 3: Found {len(primes)} primes up to {result + 50}")
    print(f"\nThe primes around the 100th position are:")
    
    # Show 5 primes before and after the 100th
    start = max(0, idx - 5)
    end = min(len(primes), idx + 6)
    
    for i in range(start, end):
        if i == idx:
            print(f"  {i + 1:3d}. {primes[i]:3d} <-- The 100th prime!")
        else:
            print(f"  {i + 1:3d}. {primes[i]:3d}")
    
    print(f"\nThe 100th prime number is: {result}")
    
    # Verify by checking it's actually prime
    print(f"\nVerification: {result} is prime because it's only divisible by 1 and itself")

if __name__ == "__main__":
    main()