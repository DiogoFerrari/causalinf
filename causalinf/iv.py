
class estimate():

    def __init__(self, formula):
        """Fit DID model

        :param formula: A formula that specifies the model
        :type formula: string
        :returns: Object of class IV
        :rtype: class

        """
        self.formula = formula

    def summary(self):
        """Summarize IV estimation 

        :returns: Print summary of IV estimation
        :rtype: None

        """
        print(self.formula)
        print("ok")
        return None
