# Playground pilot — manual protocol

**Goal:** crude preview of the effort curves before spending a cent. 15 items x 3 effort levels = 45 playground runs (~45-60 min).

**Rules:**

- One NEW chat per run (no context leakage between questions)
- If the playground has web search, TURN IT OFF (contaminates math/knowledge answers)
- Set effort via the playground's reasoning/effort control: 0.2, then 0.6, then 0.99
- Grade only the final answer line; ignore the reasoning trace
- Record 1/0 in pilot/tally.csv, plus rough response length (S/M/L)

---

## math_0000  (gold: `280`)

```text
What is the sum of all positive integers n < 100 such that n is divisible by 7 and n+1 is divisible by 3?
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0001  (gold: `19`)

```text
A bag has 5 red and 3 blue marbles. Two are drawn without replacement. What is the probability both are red, as a fraction m/n in lowest terms? Give m+n.
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0002  (gold: `1`)

```text
Compute the remainder when 2^100 is divided by 125.
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0003  (gold: `96`)

```text
How many positive divisors does 8!, factorial of 8, have?
End with the answer on its own last line, prefixed 'Final answer:'.
```

## math_0004  (gold: `60`)

```text
What is the smallest positive integer with exactly 12 divisors?
End with the answer on its own last line, prefixed 'Final answer:'.
```

## extraction_0000  (gold: `INV-2026404`)

```text
Invoice INV-2026404 — issued to Kira Eriksen, shipping to Halifax.
  1 x USB-C hub @ $155.79
  1 x headset @ $37.33
  4 x docking station @ $210.36
Invoice total: $1034.56

From the invoice above, extract the invoice number. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0001  (gold: `Toronto`)

```text
Invoice INV-2026246 — issued to Nadia Chen, shipping to Toronto.
  3 x laptop stand @ $379.87
  4 x USB-C hub @ $237.18
  2 x webcam @ $167.72
  5 x desk mat @ $390.86
  1 x keyboard @ $32.93
  5 x microphone @ $345.51
Invoice total: $6138.55

From the invoice above, extract the shipping city. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0002  (gold: `5`)

```text
Invoice INV-2026105 — issued to Jonas Fuentes, shipping to Ottawa.
  3 x desk mat @ $37.95
  4 x USB-C hub @ $94.29
  5 x headset @ $276.95
  4 x microphone @ $179.62
Invoice total: $2594.24

From the invoice above, extract the quantity of 'headset' ordered. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0003  (gold: `60.46`)

```text
Invoice INV-2026813 — issued to Jonas Haddad, shipping to Vancouver.
  4 x USB-C hub @ $295.84
  2 x microphone @ $125.86
  3 x trackball @ $392.37
  2 x monitor arm @ $60.46
Invoice total: $2733.11

From the invoice above, extract the unit price of 'monitor arm' in dollars. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0004  (gold: `INV-2026985`)

```text
Invoice INV-2026985 — issued to Nadia Baptiste, shipping to Halifax.
  4 x headset @ $282.69
  1 x desk mat @ $243.83
  1 x docking station @ $238.26
Invoice total: $1612.85

From the invoice above, extract the invoice number. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0005  (gold: `Halifax`)

```text
Invoice INV-2026713 — issued to Imani Petrov, shipping to Halifax.
  1 x laptop stand @ $124.57
  4 x microphone @ $163.53
  3 x trackball @ $272.43
Invoice total: $1595.98

From the invoice above, extract the shipping city. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0006  (gold: `2`)

```text
Invoice INV-2026505 — issued to Farid Dubois, shipping to Toronto.
  5 x microphone @ $165.52
  3 x monitor arm @ $350.50
  2 x webcam @ $46.02
  4 x trackball @ $187.94
Invoice total: $2722.90

From the invoice above, extract the quantity of 'webcam' ordered. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0007  (gold: `241.81`)

```text
Invoice INV-2026699 — issued to Nadia Larsson, shipping to Calgary.
  3 x monitor arm @ $104.30
  3 x USB-C hub @ $104.83
  1 x docking station @ $201.71
  2 x headset @ $241.81
Invoice total: $1312.72

From the invoice above, extract the unit price of 'headset' in dollars. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0008  (gold: `INV-2026975`)

```text
Invoice INV-2026975 — issued to Liam Kowalski, shipping to Vancouver.
  4 x trackball @ $168.26
  1 x headset @ $166.74
  2 x keyboard @ $200.39
Invoice total: $1240.56

From the invoice above, extract the invoice number. Reply with the value only on the last line, prefixed 'Final answer:'.
```

## extraction_0009  (gold: `Vancouver`)

```text
Invoice INV-2026451 — issued to Chloe Gupta, shipping to Vancouver.
  3 x desk mat @ $15.09
  5 x laptop stand @ $73.24
  1 x USB-C hub @ $54.06
Invoice total: $465.53

From the invoice above, extract the shipping city. Reply with the value only on the last line, prefixed 'Final answer:'.
```
