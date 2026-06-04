# tmp
import matplotlib.pyplot as plt

class estimate():
    
    def __init__(self, formula):
        # """
        # Fit DID model.

        # Parameters
        # ----------
        # formula : str
        #     A formula that specifies the model.

        # Returns
        # -------
        # DiD
        #     Object of class DiD with the fitted model.
        # """
        self.formula = formula

    def summary(self):
        # """
        # Summarize DiD estimation 
        # """
        pass

    def plot_trends(self):
        pass
        
    def plot_effects(self):
        pass

class parallel_trends():

    def __new__(self):
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=[10, 6], tight_layout=True)
        #
        ax.plot()



