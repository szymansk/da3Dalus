class Airplane:
    def __init__(self) -> None:
        self.wings={}
        self.fuselage=[]
        self.mainwings=None
        self.tailwings=None
        self.allwings=None
    
    def set_right_mainwing(self,wing):
        self.wings.update({"right_mainwing": wing})
    
    def set_left_mainwing(self,wing):
        self.wings.update({"left_mainwing": wing})
    
    def set_right_tailwing(self,wing):
        self.wings.update({"right_h_tailwing": wing})
    
    def set_left_tailwing(self,wing):
        self.wings.update({"left_h_tailwing": wing})
    
    def set_v_tailwing(self,wing):
        self.wings.update({"v_tailwing": wing})
        
