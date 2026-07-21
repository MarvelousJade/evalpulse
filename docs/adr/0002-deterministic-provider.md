# ADR 0002: Deterministic provider first

Status: accepted

The initial release ships a mock provider before any external model integration. It produces repeatable outputs without credentials or cost, supports failure fixtures, and makes regression decisions suitable for CI. External providers may be added behind the same normalized interface later.

