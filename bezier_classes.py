class Location:
    def __init__(self, x_, y_):
        self.x = x_
        self.y = y_
    def __iter__(self):
        yield self.x
        yield self.y

class Path:
    def __init__(self, path_pt1_: Location | None, path_pt2_: Location | None, ctrl_pts=None, locked=False):
        self.path_pt1 = path_pt1_
        self.path_pt2 = path_pt2_
        self.control_pts = ctrl_pts if ctrl_pts is not None else []
        self.locked = locked
    # vvv Methods vvv
    def setPt1(self, pos_: Location):
        self.path_pt1 = pos_
    def setPt2(self, pos_: Location):
        self.path_pt2 = pos_
    def addCtrlPt(self, pos_: Location):
        self.control_pts.append(pos_)
    def lock(self):
        self.locked = True