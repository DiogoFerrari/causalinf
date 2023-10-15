
class estimate():

    def __init__(self, formula):
        """Fit DID model

        :param formula: A formula that specifies the model
        :type formula: string
        :returns: Object of class DiD
        :rtype: class

        """
        self.formula = formula

    def summary(self):
        """Summarize DiD estimation 

        :returns: Print summary of DiD estimation
        :rtype: None

        """
        print(self.formula)
        print("ok")
        return None
