---

hide:

-   toc

---

Some core functions in `causalinf` are standardized across the many
submodules used for different causal inference methods. The main ones
are:

| Task                              | Basic function                       |
|-----------------------------------|--------------------------------------|
| Check causal modeling assumptions | `<submodule>.check_assumptions()`    |
| Estimate causal model             | `<submodule>.estimate()`             |
| Run sensitivity analysis          | `<submodule>.sensitivity_analysis()` |
| Summarize the results             | `<submodule>.summary()`              |
| Examples(1)                       | `<submodule>examples()`              |

*Note: (1) Each submodule contains some pre-defined examples to
illustrate `causalinf` usage. See [Examples.](../examples/)*

For details of these functions, see [Basic Functions](../assumptions/)
subsections.

For method-specific features, see
[Methods](../../methods/gcm/introduction).

For comprehensive applied examples, see [Case
Studies](../../case-studies/did-card1994minimum).
