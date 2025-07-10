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

def generate_primes(limit):
    """Generate all prime numbers up to a given limit."""
    primes = []
    for num in range(2, limit + 1):
        if is_prime(num):
            primes.append(num)
    return primes

def sieve_of_eratosthenes(limit):
    """Generate primes using the Sieve of Eratosthenes algorithm."""
    if limit < 2:
        return []
    
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i*i, limit + 1, i):
                sieve[j] = False
    
    return [i for i in range(2, limit + 1) if sieve[i]]

if __name__ == "__main__":
    # Test the functions
    print("First 20 primes:", generate_primes(20))
    print("Primes up to 50 (Sieve):", sieve_of_eratosthenes(50))
    print("Is 17 prime?", is_prime(17))
    print("Is 18 prime?", is_prime(18))