window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"], ["$$", "$$"]],
    processEscapes: true,
    processEnvironments: true,
    tags: "ams",
    macros: {
      // 1. Simulate 'booktabs' commands
      toprule: "\\hline\\hline",      // Double line for top
      midrule: "\\hline",            // Single line for middle
      bottomrule: "\\hline\\hline",   // Double line for bottom
      
      // 2. Simulate 'multicol' (if you really needed it, though \multicolumn works natively)
      // This is just an example of how to map commands
      // mycommand: ["\\mathbf{#1}", 1] 
    }
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};
