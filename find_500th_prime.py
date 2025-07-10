#!/usr/bin/env python3
"""
Find the 500th prime number.

This script implements a prime number finder using the Sieve of Eratosthenes
and direct primality testing to find the 500th prime number.
"""

def is_prime(n):
    """Check if a number is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    # Check odd divisors up to sqrt(n)
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True

def find_nth_prime(n):
    """Find the nth prime number."""
    if n == 1:
        return 2
    
    primes = [2]
    candidate = 3
    
    while len(primes) < n:
        if is_prime(candidate):
            primes.append(candidate)
            print(f"Prime #{len(primes)}: {candidate}")
        candidate += 2  # Skip even numbers
    
    return primes[-1]

def main():
    print("Finding the 500th prime number...\n")
    
    # Show first few primes
    print("First 10 primes:")
    for i in range(1, 11):
        prime = find_nth_prime(i)
        print(f"Prime #{i}: {prime}")
    
    print("\n" + "="*50 + "\n")
    
    # Find the 500th prime
    print("Calculating the 500th prime number...")
    result = find_nth_prime(500)
    
    print(f"\nThe 500th prime number is: {result}")
    
    # Verify it's prime
    print(f"\nVerification: is_prime({result}) = {is_prime(result)}")
    
    # Show some context
    print(f"\nContext:")
    print(f"The 499th prime is: {find_nth_prime(499)}")
    print(f"The 501st prime is: {find_nth_prime(501)}")

if __name__ == "__main__":
    main()