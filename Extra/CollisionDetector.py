import logging

import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.TopoDS as OTopo

import Extra.mydisplay as myDisplay


class CollisionDetector:
    def __init__(self):
        logging.info(f"Initialising CollisionDetector")
        self.m = myDisplay.myDisplay.instance()

    def check_shapes_colission(self, shape1: OTopo.TopoDS_Shape, shape2: OTopo.TopoDS_Shape, name1: str = "shape1",
                               name2: str = "shape2", expectation: bool = True):
        """
        This method check if the 2 given Shapes overlap/collide.
        By default, it is expected that they do. If they collide it returs True, if they don't False.
        You can change the expectation with the expectation param
        :param shape1: primary shape
        :param shape2: shape to test for collision
        :param name1: name of the first shape for logging Default: "shape1"
        :param name2: name of the second shape for logging Defaul: "shape2"
        :param expectation: do you expect them to collide. Default:True
        :return: True if collision matches expectation
        """
        overlap_shape = OAlgo.BRepAlgoAPI_Common(shape1, shape2).Shape()

        if OTopo.TopoDS_Iterator(overlap_shape).More():
            kollision = True
        else:
            kollision = False
        logging.info(f"Collision check between {name1} and {name2}: {expectation=} result= {kollision}")

        if kollision == expectation:
            return True
        else:
            if kollision and expectation == False:
                logstr = f"Unexpected collision between {name1} and {name2}"
                logging.error(logstr)
                self.m.display_colission(overlap_shape, shape1, shape2, logstr)
            if not kollision and expectation == True:
                logstr = f"Expected collision between {name1} and {name2} does not exist "
                logging.error(logstr)
                self.m.display_colission(overlap_shape, shape1, shape2, logstr)
            return False

    def check_namedshape_collision(self, shape1, shape2, expectation):
        """

        :param shape1:
        :param shape2:
        :param expectation:
        :return:
        """
        return self.check_shapes_colission(shape1.shape(), shape2.shape(), shape1.name(), shape2.name(), expectation)

    def multiple_collision_check(self, test_cases):
        """

        :param test_cases:
        :return:
        """
        for named_shape in test_cases:
            for a_test in test_cases[named_shape]:
                named_shape_to_test = a_test[0]
                expectation = a_test[1]
                self.check_namedshape_collision(named_shape, named_shape_to_test, expectation)
