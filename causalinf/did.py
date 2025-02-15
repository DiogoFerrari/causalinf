
class estimate():
    
    def __init__(self, formula):
        """
        Fit DID model.

        Parameters
        ----------
        formula : str
            A formula that specifies the model.

        Returns
        -------
        DiD
            Object of class DiD with the fitted model.
        """
        self.formula = formula

    def summary(self):
        """
        Summarize DiD estimation 
        """
        print(self.formula)
        return None

    def plot_trends(self):
        print('ok')
        
    def plot_effects(self):
        print('ok')



