from pygame.locals import *
from pygame.constants import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

from OBJFileLoader import *

import numpy as np
from collections import defaultdict

########################################### Transformations ####################################################
class Transform:
    def __init__(self, translation=(0,0,0), rotation=(0,0,0), scale=(1,1,1)):
        self.translation = translation  # (x, y, z)
        self.rotation = rotation        # (angle_degrees, x_axis, y_axis, z_axis)
        self.scale = scale              # (sx, sy, sz)

def apply_transform_to_point(point, transform):
    # Convert the point to a numpy array
    p = np.array(point, dtype=float)

    # 1. Scale
    p = p * np.array(transform.scale)

    # 2. Rotation around Y-axis
    angle_rad = np.radians(transform.rotation[0])  # assuming rotation is (angle, x, y, z)
    if transform.rotation[1:] == (0,1,0):  # if rotating around Y-axis
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        rotation_matrix = np.array([
            [ cos_a, 0, sin_a],
            [ 0,     1, 0    ],
            [-sin_a, 0, cos_a]])
        p = np.dot(rotation_matrix, p)  # matrix multiplication

    # 3. Translation
    p = p + np.array(transform.translation)

    return list(p)

def apply_transform_to_mesh(obj, transform):
    transformed_vertices = []
    for v in obj.vertices:
        transformed_v = apply_transform_to_point(v, transform)
        transformed_vertices.append(transformed_v)
    obj.vertices = transformed_vertices
    obj.rebuild_gl_list()
    #return transformed_vertices


########################################### Drawing Functions ####################################################
# draw the mesh, its edges and vertices, and bounding volume
#   bv_type = "sphere" or "AABB"
def draw_mesh(obj): 
    glEnable(GL_LIGHTING)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)

    # Material properties for specular highlight
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.5, 0.5, 0.5, 1.0))   # less shiny white
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)                  # [0–128], higher = tighter highlight

    glPushMatrix()
    glCallList(obj.gl_list)
    glPopMatrix()

def draw_AABB(min_coords, max_coords, center):
    # Calculate size of the box along each axis
    size_x = max_coords[0] - min_coords[0]
    size_y = max_coords[1] - min_coords[1]
    size_z = max_coords[2] - min_coords[2]

    # glutWireCube draws a cube of size 1 centered at (0,0,0), so we scale
    glPushAttrib(GL_POLYGON_BIT)
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 1.0, 1.0)
    glLineWidth(1.0)
    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    glPushMatrix()
    glTranslatef(center[0], center[1], center[2])
    glScalef(size_x, size_y, size_z)
    glutWireCube(1.0)
    glPopMatrix()

    glEnable(GL_LIGHTING)
    glPopAttrib()

def get_AABB(center, size):
    half = size / 2.0
    min_bound = center - half
    max_bound = center + half
    return min_bound, max_bound

########################################### In-Class Exercises: Collision Detection ####################################################
#   Collision if their ranges (min, max) on EACH axis (x, y, z) overlap
def collisionTest_AABBs(min_coords1, max_coords1, min_coords2, max_coords2):
    for i in range(3):  # 0=x, 1=y, 2=z
        if max_coords1[i] < min_coords2[i] or min_coords1[i] > max_coords2[i]:
            return False
    return True

# Class to handle the obstacles in the game
class Obstacles:
    def __init__(self, object, places=[], spinning=False):
        self.places = places
        self.spinning = spinning
        self.angle = 0

        model_path = os.path.join("./resources/models", object+".obj")
        if not os.path.exists(model_path):
            raise ValueError(f"OBJ file not found: {model_path}")
        
        self.obj = OBJ(model_path, swapyz=False)
        self.objs = []
        for place in self.places:
            # Apply transformations to each obj
            transform = Transform(translation=place)
            obj = OBJ(model_path, swapyz=False)
            apply_transform_to_mesh(obj, transform)
            self.objs.append(obj)

    def drawMeshes(self):
        for place in self.places:
            glPushMatrix()
            glTranslatef(*place)
            # Apply rotation if spinning
            if self.spinning:
                self.angle += 2
                glRotatef(self.angle, 0, 1, 0)
            draw_mesh(self.obj)
            glPopMatrix()

    def collision(self, car_position, car_size):
        for obj in self.objs:
            place = self.objs.index(obj)
            min_coords, max_coords = obj.cal_minMax()
            min_car, max_car = get_AABB(car_position, car_size)
            if collisionTest_AABBs(min_coords, max_coords, min_car, max_car):
                del self.places[place]
                self.objs.remove(obj)  # Remove the obj if a collision is detected
                return True
        return False