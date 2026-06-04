---

hide:

- toc

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
| Examples\*                        | `<submodule>examples()`              |

*\* Each submodule contains some pre-defined examples to illustrate
`causalinf` application. See [Examples.](../examples/)*

There are many other method-specific functions. See
[Methods](../methods/overview.md) for details.

For comprehensive applied examples, see [Case
Studies](../../case-studies/overview).
