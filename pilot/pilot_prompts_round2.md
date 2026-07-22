# Playground pilot round 2 — real AIME-25, hard math

**Question this answers for free:** does accuracy DROP at low effort on genuinely hard math? If yes, the effort knee exists and the paid sweep will find it. If AIME holds at 0.2, we need a harder tier (GPQA-style).

**Protocol:** same as round 1 — fresh chat per run, web search OFF (critical here: these are published competition problems, search would contaminate), efforts 0.2 / 0.6 / 0.99, grade the final integer only.

8 items x 3 efforts = 24 runs. Record in pilot/tally_round2.csv.

---

## math_0000  (gold: `237`)

```text
Let $A$ be the set of positive integer divisors of $2025$. Let $B$ be a randomly selected subset of $A$. The probability that $B$ is a nonempty set with the property that the least common multiple of its element is $2025$ is $\frac{m}{n}$, where $m$ and $n$ are relatively prime positive integers. Find $m+n$.
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0001  (gold: `504`)

```text
An isosceles trapezoid has an inscribed circle tangent to each of its four sides. The radius of the circle is $3$, and the area of the trapezoid is $72$. Let the parallel sides of the trapezoid have lengths $r$ and $s$, with $r \neq s$. Find $r^2+s^2$
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0002  (gold: `468`)

```text
Six points $A, B, C, D, E,$ and $F$ lie in a straight line in that order. Suppose that $G$ is a point not on the line and that $AC=26, BD=22, CE=31, DF=33, AF=73, CG=40,$ and $DG=30.$ Find the area of $\triangle BGE.$
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0003  (gold: `240`)

```text
Let\[f(x)=\frac{(x-18)(x-72)(x-98)(x-k)}{x}.\]There exist exactly three positive real values of $k$ such that $f$ has a minimum at exactly two real values of $x$. Find the sum of these three values of $k$.
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0004  (gold: `77`)

```text
Let $k$ be a real number such that the system \begin{align*} &|25 + 20i - z| = 5 \ &|z - 4 - k| = |z - 3i - k| \end{align*} has exactly one complex solution $z$. The sum of all possible values of $k$ can be written as $\frac{m}{n}$, where $m$ and $n$ are relatively prime positive integers. Find $m + n$. Here $i = \sqrt{-1}$.$
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0005  (gold: `104`)

```text
Let ${\triangle ABC}$ be a right triangle with $\angle A = 90^\circ$ and $BC = 38.$ There exist points $K$ and $L$ inside the triangle such\[AK = AL = BK = CL = KL = 14.\]The area of the quadrilateral $BKLC$ can be expressed as $n\sqrt3$ for some positive integer $n.$ Find $n.$
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0006  (gold: `81`)

```text
The $27$ cells of a $3 \times 9$ grid are filled in using the numbers $1$ through $9$ so that each row contains $9$ different numbers, and each of the three $3 \times 3$ blocks heavily outlined in the example below contains $9$ different numbers, as in the first three rows of a Sudoku puzzle. [asy] unitsize(20);  add(grid(9,3));  draw((0,0)--(9,0)--(9,3)--(0,3)--cycle, linewidth(2)); draw((3,0)--(3,3), linewidth(2)); draw((6,0)--(6,3), linewidth(2));  real a = 0.5;  label("5",(a,a)); label("6",(1+a,a)); label("1",(2+a,a)); label("8",(3+a,a)); label("4",(4+a,a)); label("7",(5+a,a)); label("9",(6+a,a)); label("2",(7+a,a)); label("3",(8+a,a));  label("3",(a,1+a)); label("7",(1+a,1+a)); label("9",(2+a,1+a)); label("5",(3+a,1+a)); label("2",(4+a,1+a)); label("1",(5+a,1+a)); label("6",(6+a,1+a)); label("8",(7+a,1+a)); label("4",(8+a,1+a));  label("4",(a,2+a)); label("2",(1+a,2+a)); label("8",(2+a,2+a)); label("9",(3+a,2+a)); label("6",(4+a,2+a)); label("3",(5+a,2+a)); label("1",(6+a,2+a)); label("7",(7+a,2+a)); label("5",(8+a,2+a));  [/asy] The number of different ways to fill such a grid can be written as $p^a \cdot q^b \cdot r^c \cdot s^d$ where $p$, $q$, $r$, and $s$ are distinct prime numbers and $a$, $b$, $c$, $d$ are positive integers. Find $p \cdot a + q \cdot b + r \cdot c + s \cdot d$.
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0007  (gold: `70`)

```text
Find the sum of all integer bases $b>9$ for which $17_b$ is a divisor of $97_b.$
End with the answer on its own last line, prefixed 'Final answer:'.
```
