---
hide:
  - toc
  - navigation
---

  <div class="image">
    <!-- <img src="https://github.com/DiogoFerrari/causalinf/blob/master/docs/causalinf.png?raw=True" alt="Description" style="max-width: 500px; margin-left: 10px"> -->
    <!-- <img src="./causalinf.png" alt="Description" style="max-width: 1000px; margin-left: 0px"> -->
	<!-- NOTE: style="max-width: 100%; height: auto;"  makes the image auto-shrink for smartphones-->
<div align="center">
    <img src="./_css/causalinf.png" alt="" style="max-width: 100%; height: auto;">
</div>
  </div>
  
  
<h1 style="text-align:center">Causal Inference Collection in Python</h1>
<div align="center">
  <!-- <a href="https://docs.rs/polars/latest/polars/"> -->
  <!--   <img src="https://docs.rs/polars/badge.svg" alt="Rust docs latest"/> -->
  <!-- </a> -->
  <!-- <a href="https://crates.io/crates/polars"> -->
  <!--   <img src="https://img.shields.io/crates/v/polars.svg" alt="Rust crates Latest Release"/> -->
  <!-- </a> -->
  <a href="https://pypi.org/project/causalinf/">
    <img src="https://img.shields.io/pypi/v/causalinf.svg" alt="PyPI Latest Release"/>
  </a>
  <!-- <a href="https://app.netlify.com/sites/diogoferrari/deploys"> -->
  <!--   <img src="https://api.netlify.com/api/v1/badges/92e92c9d-e001-43c4-b925-daae5b320996/deploy-status"/> -->
  <!-- </a> -->
  
  <!-- <a href="https://doi.org/10.5281/zenodo.7697217"> -->
  <!--   <img src="https://zenodo.org/badge/DOI/10.5281/zenodo.7697217.svg" alt="DOI Latest Release"/> -->
  <!-- </a> -->
</div>

 <!-- dprint-ignore-start -->
!!! info "Note" 
    <center>The package is in the development stage and will be available soon. </center>
<!-- dprint-ignore-end -->


 **causalinf** is a module for **causal inference in Python**. It provides a set of submodules with implementation of different methods for causal inference. They include:


1. [Graphical Causal Models](./methods/gcm/introduction) (**GCM**)
       1. [Structural Causal Models](./methods/scm/) (**SCM**)
	   2. [Causal Bayesian Networds](./methods/cbn/) (**CBN**)
2. Selection on Observables (**SoO**)
3. Difference-in-Differences (**DiD**)
4. Instrumental Variables (**IV**)
5. Regression Discontinuity (**RD**)
6. Mediation analysis (**MA**)
7. Matching Methods (**MM**)


For each method, these **functionalities** are provided:


1. Assessment of the plausibility of causal identification **assumptions**
2. **Estimation** and **inference** of the causal effects
3. **Reporting** the summary results (text, LaTeX, etc.)
4. Conducting **sensitivity** analysis

