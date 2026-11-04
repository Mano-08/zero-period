# Unit 2: Functions

Ms. Sharma's notes, Class 12-B. Page markers like `[p.6]` match the printed handout.

---

## [p.6] 2.1 Defining and calling a function

A function is a named block of code you can run whenever you need it.

```python
def greet(name):          # definition: nothing runs yet
    print("Hello,", name)

greet("Riya")             # call: now the body runs
greet("Arjun")
```

- `def` only **defines** the function. The body runs when you **call** it.
- The body runs again on every call. Defining once and calling many times is the point.

---

## [p.7] 2.2 Parameters and arguments

- **Parameter:** the name in the definition (`name` above).
- **Argument:** the value you pass in the call (`"Riya"`).

```python
def area(length, width):      # parameters
    return length * width

area(5, 3)                    # arguments: length=5, width=3
area(width=3, length=5)       # keyword arguments: order doesn't matter
```

Inside the function, a parameter is an ordinary local variable that starts with the
argument's value.

---

## [p.8] 2.3 Return vs print. Read this twice.

This is the most common mistake in Unit 2, and it comes back in Unit 3.

- `print(x)` **shows** `x` on the screen. The program can't use what was printed.
- `return x` **hands `x` back** to whoever called the function. The caller can store
  it, add to it, or pass it on.

```python
def double_print(n):
    print(n * 2)       # shows 10, gives nothing back

def double_return(n):
    return n * 2       # gives 10 back

a = double_print(5)    # screen shows 10, but a is None
b = double_return(5)   # screen shows nothing, but b is 10
print(a, b)            # None 10
```

**Rule:** if the function's job is to *compute* something, it should `return` it. A
function with no `return` gives back `None`.

`return` also **ends the function immediately**. Nothing after it runs.

---

## [p.9] 2.4 Scope: local and global

A variable created inside a function is **local**. It exists only while that call is
running.

```python
def f():
    x = 10        # local to f
    return x

f()
print(x)          # NameError: x is not defined out here
```

Every call gets **fresh** local variables. Two calls to the same function don't share
their locals. Remember this for recursion: each call has its own `n`.

---

## [p.10] 2.5 Functions calling functions

A function can call another function. The caller **waits** until the called function
returns, then carries on from the same line.

```python
def square(n):
    return n * n

def sum_of_squares(a, b):
    return square(a) + square(b)   # waits for square(a), then square(b)

print(sum_of_squares(3, 4))        # 25
```

Python keeps track of who is waiting for whom in the **call stack**. Unit 3 is about
a function that calls *itself*, and then the call stack really matters.
