class Airplane:
    def __init__(self, airplane_configuration) -> None:
        self.airplane_configuration= airplane_configuration
        self.wings={}
        self.fuselage=[]
    
    def set_right_mainwing(self,wing):
        self.wings.update({"rightWing": wing})
    
    def set_left_mainwing(self,wing):
        self.wings.update({"leftWing": wing})
    
    def set_right_tailwing(self,wing):
        self.wings.update({"right"})