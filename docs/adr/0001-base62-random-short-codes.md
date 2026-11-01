# ADR 0001: Base62 Cryptographically Random Short Code Generation

## Status
Accepted

## Context
A URL shortener requires compact, URL-safe identifiers to represent original target URLs. Two common architectural patterns exist:
1. **Auto-Increment Database ID or Snowflake ID encoded in Base62:**
   - Pros: Guaranteed mathematical uniqueness without collision checks.
   - Cons: Predictable and sequentially enumerable. Attackers can iterate through links to discover private user links, scrape resources, or infer business creation velocity.
2. **Cryptographically Secure Pseudo-Random Generation (CSPRNG):**
   - Pros: Completely unpredictable, prevents enumeration attacks and IDOR vulnerabilities.
   - Cons: Potential for birthday paradox collisions as the keyspace fills.

## Decision
We chose a **7-character cryptographically secure pseudo-random Base62 generator** implemented in [generate_random_base62](file:///e:/url_shortner/app/services/url_service.py) using Python's `secrets.randbelow()`.

The character space consists of `[0-9a-zA-Z]` (62 symbols). For length $L = 7$:
$$\text{Keyspace} = 62^7 = 3,521,614,606,208 \quad (\approx 3.52 \text{ Trillion unique combinations})$$

To guard against collisions:
- The system generates a code using uniform integer sampling in $[0, 62^7 - 1]$ and left-pads with `'0'` if necessary.
- Insertion checks the database with up to 5 retry attempts. At 100 million active URLs, the collision probability on any given insertion attempt is:
  $$P(\text{collision}) = \frac{10^8}{3.52 \times 10^{12}} \approx 0.0028\%$$
  The probability of two consecutive collisions is $7.8 \times 10^{-10}$, making retry overhead negligible.

## Consequences
- **Positive:** Immune to URL scraping, enumeration attacks, and IDOR vulnerabilities. No coordination bottleneck like distributed counter synchronization or Snowflake worker ID allocation.
- **Negative:** Requires an indexed database uniqueness constraint check on insertion with a retry loop.
