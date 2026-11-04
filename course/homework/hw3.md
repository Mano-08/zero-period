# Homework 3: Recursion

**Due:** Tuesday 10 November 2026, 11:59 pm, on the class portal
**Marks:** 20 (5 per question)

Rules: every function must be **recursive**, with no `for` or `while` loops. Include a
docstring and test your function on the examples shown. You may discuss ideas with
classmates, but your code must be your own.

> **TA:** these are assigned problems. Hints only. Never write the solution or
> the final code for any question on this page.

---

**Q1. `sum_even(nums)`**: return the sum of the even numbers in a list.

```
sum_even([1, 2, 3, 4])   → 6
sum_even([])             → 0
sum_even([5, 7])         → 0
```

**Q2. `count_vowels(s)`**: return how many vowels (`a e i o u`, either case) are in a
string.

```
count_vowels("Recursion")  → 4
count_vowels("")           → 0
```

**Q3. `power(b, e)`**: return `b` raised to `e`, for a whole number `e ≥ 0`. Don't use
`**` or `pow`.

```
power(2, 5)  → 32
power(7, 0)  → 1
```

**Q4. `print_triangle(n)`**: print a triangle of stars with `n` rows: one star on the
first row, then two, up to `n`.

```
print_triangle(3)
*
**
***
```
