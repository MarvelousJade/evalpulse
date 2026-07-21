# ADR 0001: PostgreSQL is authoritative

Status: accepted

Evaluation inputs, lifecycle transitions, results, and comparison decisions are persisted in PostgreSQL. Redis is limited to replaceable delivery, cache, cancellation, and progress data. This makes completed evaluations durable across broker restarts and gives reconnecting clients an auditable state to reconcile against.

