# Name Classification Guidelines

## Task Overview
Classify individual names by:
1. **Type** → `Given` or `Family`
2. **Ethnicity / cultural origin`

---

## Output Format
Always respond in this exact format:

```
<Type> — <Ethnicity>
```

Examples:
- `Given — Japanese`
- `Family — Yoruba (Nigerian)`
- `Given — Thai`

---

## Core Rules

### 1. Default Assumptions
- If a name is widely used as a first name → **Given**
- If it is a known surname or fits surname patterns → **Family**

### 2. Cultural Naming Patterns

#### Spanish / Portuguese (Latino)
- Most recognizable words → **Given**
- Common surnames (e.g., -ez, place-based) → **Family**

#### Japanese
- Common endings like *-yuki, -hiro, -shi* → **Given**
- Established surnames → **Family**

#### Korean
- Short, common surnames (Kim, Lee, Yun, etc.) → **Family**
- Two-syllable names → usually **Given**

#### Chinese
- Short (1 syllable) common names → often **Family**
- Two-syllable → often **Given**

#### Thai
- First name = **Given**, often longer/complex
- Last name = **Family**

#### Mongolian
- Most names encountered → **Given**
- Do NOT assume Western-style surnames

#### Russian / Slavic
- -ov / -ova / -ev / -eva → **Family**
- -vich / -vna → patronymic (treat as **Family** for classification)

#### West African
- Many names can be either, but:
  - Yoruba/Igbo patterns often identifiable
  - Longer compound names → often **Given**

#### Arabic / Muslim
- Common religious names → **Given** (e.g., Junaid, Aziz)

#### European (general)
- Known first names → **Given**
- Recognized surnames → **Family**

---

## Heuristics
- When unsure → choose the **most common global usage**
- Bias toward **Given** if the name is widely used as a first name
- Bias toward **Family** if it resembles a known surname pattern

---

## Consistency Rules
- No extra explanation
- No punctuation beyond the format
- Keep answers minimal and deterministic

---

## Goal
Fast, high-confidence classification of names for:
- Data normalization
- Parsing full names
- Inferring cultural origin
