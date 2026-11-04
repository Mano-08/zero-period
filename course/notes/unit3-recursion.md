# Unit 3: Recursion

Ms. Sharma's notes, Class 12-B. Page markers like `[p.14]` match the printed handout.

---

## [p.11] 3.1 What recursion is

A function is **recursive** when it calls itself to solve a **smaller version of the
same problem**.

Think of a **stack of plates**. To count the plates: if there are none, the answer is
0. Otherwise, take one plate off, count the rest the same way, and add 1.

Every recursive function has two parts:

1. **Base case:** the smallest version of the problem. You answer it directly,
   with no recursive call.
2. **Recursive case:** do a little work, and call the function on a smaller input.

If you can't name both parts, you don't have a recursive function yet.

---

## [p.12] 3.2 Anatomy: factorial

`n!` ("n factorial") is `n × (n−1) × … × 1`. So `4! = 4 × 3 × 2 × 1 = 24`.

Notice that `4! = 4 × 3!`. The big problem contains a smaller copy of itself.

```python
def factorial(n):
    if n == 0:                    # base case
        return 1
    return n * factorial(n - 1)   # recursive case: smaller input (n - 1)
```

**Why is `0!` equal to 1?** It's the **empty product**. Adding nothing leaves you with 0,
the "do-nothing" number for addition. Multiplying nothing leaves you with 1, the
"do-nothing" number for multiplication. If `factorial(0)` returned 0, every factorial
would become 0, because the 0 would be multiplied into everything on the way back.

---

## [p.13] 3.3 Choosing the base case

Ask three questions:

1. **What is the smallest input?** For `factorial`, `n = 0`. For a list, the empty list `[]`.
   For a string, the empty string `""`.
2. **What is the answer for that input?** Work it out by hand. Don't guess.
3. **Does every recursive call get closer to it?** `n - 1` moves toward 0. `nums[1:]`
   moves toward `[]`.

**A common bug:** using `if n == 1: return 1` as the only base case. It works for
`factorial(5)`, but `factorial(0)` calls `factorial(-1)`, then `factorial(-2)`, and so on
forever. It never reaches 1. See p.17 for what happens then.

> **Tip:** the base case is about the smallest *input*, not the last number you
> multiply.

---

## [p.14] 3.4 Tracing: the call stack and unwinding

Every call waits for the call it made. Calls pile up like plates until one of them
reaches the base case. Then they finish **in reverse order**: the last call made is the
first to finish. That's **unwinding**.

Trace of `factorial(3)`:

```
factorial(3) waits for factorial(2)            going DOWN (calls pile up)
  factorial(2) waits for factorial(1)
    factorial(1) waits for factorial(0)
      factorial(0) returns 1                   base case reached
    factorial(1) returns 1 * 1 = 1             coming back UP (unwinding)
  factorial(2) returns 2 * 1 = 2
factorial(3) returns 3 * 2 = 6
```

- Going **down**, nothing gets multiplied yet. Every call is waiting.
- Coming back **up**, each call finishes its line: `n * <the value that came back>`.
- Each call has its **own** `n` (see p.9). The `n` in `factorial(3)` stays 3 the whole time.

**How to trace on paper:** draw one box per call, write `n` inside it, and fill in
the return value only when the call below has returned.

---

## [p.15] 3.5 Return values travel back up

The value returned by the inner call **becomes part of the outer call's expression**.

```python
def sum_list(nums):
    if nums == []:                          # base case: empty list
        return 0
    return nums[0] + sum_list(nums[1:])     # first item + sum of the rest
```

`sum_list([4, 5])` → `4 + sum_list([5])` → `4 + (5 + sum_list([]))` → `4 + (5 + 0)` → `9`.

**Bug: forgetting `return` in the recursive case.**

```python
def sum_list_buggy(nums):
    if nums == []:
        return 0
    nums[0] + sum_list_buggy(nums[1:])      # computed, then thrown away!
```

This version computes the right numbers but never hands them back, so the outer call
gets `None`. You'll see `TypeError: unsupported operand type(s) for +: 'int' and
'NoneType'` or a plain `None`. Every path through a recursive function that should
produce a value needs a `return` (p.8).

**Print vs return again:** printing inside a recursive function shows values on the
screen, but the caller still gets `None` unless you `return`.

---

## [p.16] 3.6 Order of work: before or after the recursive call

Where you put the work changes the order of the output.

```python
def countdown(n):
    if n == 0:
        return
    print(n)            # work BEFORE the call → runs on the way down
    countdown(n - 1)

def countup(n):
    if n == 0:
        return
    countup(n - 1)
    print(n)            # work AFTER the call → runs on the way back up
```

`countdown(3)` prints `3 2 1`. `countup(3)` prints `1 2 3`.

Output can look "reversed" because the `print` after the call has to wait until every
deeper call has finished (p.14).

---

## [p.17] 3.7 RecursionError and debugging

If the base case is never reached, calls keep piling up until Python stops you:

```
RecursionError: maximum recursion depth exceeded
```

Python's default limit is about 1000 nested calls. Hitting it almost always means:

- there is **no base case**, or
- the base case **can't be reached** from some inputs (the `n == 1` bug on p.13), or
- the recursive call **doesn't make the input smaller** (for example `f(n)` calling `f(n)`).

**Debug it like this:**

1. Put `print("called with", n)` as the first line of the function.
2. Run it on a small input. Do the values move toward the base case?
3. Check the base case with the **smallest possible input** (0, `[]`, `""`).

Don't "fix" a RecursionError by raising the limit. Fix the base case.

---

## [p.18] 3.8 Recursion vs loops

- Anything you can do with recursion, you can also do with a loop, and the other way round.
- Recursion is natural when the problem **contains smaller copies of itself**: nested
  lists, folders inside folders, family trees, and divide-and-conquer methods like
  binary search.
- Loops are often simpler for plain counting and running totals.
- Each recursive call uses some memory on the call stack, so very deep recursion
  (thousands of levels) can fail where a loop would be fine.

The point of this unit is to learn to **think** recursively: trust the smaller call
to do its job, and focus on one step plus the base case.

---

## [p.19] 3.9 Worked example: sum of digits

Problem: `digit_sum(4721)` should return `4 + 7 + 2 + 1 = 14`.

1. **Smallest input:** a single digit, `n < 10`. The answer is `n` itself.
2. **One step:** the last digit is `n % 10`. The rest of the number is `n // 10`.
3. **Trust the smaller call:** `digit_sum(n // 10)` gives the sum of the other digits.

```python
def digit_sum(n):
    if n < 10:                              # base case
        return n
    return n % 10 + digit_sum(n // 10)      # last digit + sum of the rest
```

Trace: `digit_sum(4721)` = `1 + digit_sum(472)` = `1 + (2 + digit_sum(47))`
= `1 + (2 + (7 + digit_sum(4)))` = `1 + (2 + (7 + 4))` = `14`.

---

## [p.20] 3.10 Practice (not homework)

Try these yourself. They aren't marked.

1. `reverse("abc")` → `"cba"`. Hint: the reverse of a string is the reverse of the
   rest, followed by the first letter.
2. `count_to(n)` prints `1` to `n` using recursion and no loop. Which page tells you
   where to put the `print`?
3. `sum_to(n)` returns `1 + 2 + … + n`. What is `sum_to(0)`?
