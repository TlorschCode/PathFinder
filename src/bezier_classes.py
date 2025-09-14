class Location:
    def __init__(self, x_, y_):
        self.x = x_
        self.y = y_
    def __iter__(self):
        yield self.x
        yield self.y
    def __eq__(self, other):
        return isinstance(other, Location) and self.x == other.x and self.y == other.y

class Path:
    def __init__(self, path_pt1_: Location | None, path_pt2_: Location | None, ctrl_pts=None, locked=False):
        self.path_pt1 = path_pt1_
        self.path_pt2 = path_pt2_
        self.control_pts = ctrl_pts if ctrl_pts is not None else []
        self.locked = locked
        self.score = 0
    def __eq__(self, other):
        return (
            isinstance(other, Path)
            and self.path_pt1 == other.path_pt1
            and self.path_pt2 == other.path_pt2
            and self.control_pts == other.control_pts
            and self.locked == other.locked
        )
    # vvv Methods vvv
    def setPt1(self, pos_: Location):
        self.path_pt1 = pos_
    def setPt2(self, pos_: Location):
        self.path_pt2 = pos_
    def addCtrlPt(self, pos_: Location):
        self.control_pts.append(pos_)
    def lock(self):
        self.locked = True