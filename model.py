import pygame
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import numpy as np

#      Construct a 3x3 rotation matrix (no need Homogeneous) and multiply it with the input vector
#      rot_axis: "X", "Y", or "Z"
#      Return the rotated vector.
def rotate_vector(vector, angle_degrees, rot_axis):
    # Convert angle degrees to radians
    radians = np.radians(angle_degrees)

    # Construct a 3x3 rotation matrix using np.array based on angle and rotation axis
    if rot_axis == "Y":
        R = np.array([[np.cos(radians), 0, np.sin(radians)],
                    [0, 1, 0],
                    [-np.sin(radians), 0, np.cos(radians)]])
        rotate_vector = np.dot(R, vector)
    elif rot_axis == "X":
        R = np.array([[1, 0, 0],
                    [0, np.cos(radians), -np.sin(radians)],
                    [0, np.sin(radians), np.cos(radians)]])
        rotate_vector = np.dot(R, vector)
    elif rot_axis == "Z":
        R = np.array([[np.cos(radians), np.sin(radians), 0],
                    [-np.sin(radians), np.cos(radians), 0],
                    [0, 0, 1]])
        rotate_vector = np.dot(R, vector)

    return rotate_vector

class Camera:
    def __init__(self, run, lane=0, movement=0):
        self.view_mode = 'front'
        self.angle = 0
        # camera parameters
        if run:
            self.eye_pos = np.array([lane, 20.0, 50.0]) # initial setting for the front view
            self.look_at = np.array([lane, 10.0, movement])
        else:
            self.eye_pos = np.array([0, 40.0, -50.0]) # initial setting for the front view
            self.look_at = np.array([0, 15.0, 0])

        self.view_up = np.array([0.0, 1.0, 0.0])

    def rotate(self, horizontal, zoom):
        new_eye_pos = np.copy(self.eye_pos)
        # calculate the current gaze vector
        gaze_vector = self.look_at - self.eye_pos

        # calculate new look-at point
        gaze_vector = rotate_vector(gaze_vector, horizontal, "Y")

        # alculate the current look-at point
        new_eye_pos = self.look_at - gaze_vector

        ## calculate new eye position by moving the camera along the gaze vector by zoom_distance
        gaze_vector_unit = gaze_vector / np.linalg.norm(gaze_vector)

        new_eye_pos += gaze_vector_unit * zoom

        return new_eye_pos
        
    # Update camera parameters (eye_pos and look_at) based on the new variables
    def update_view(self, lane, movement, crashed = False):
        new_eye_pos = np.copy(self.eye_pos)
        new_lookat = np.copy(self.look_at)
        
        # if the view mode is "first_person",
        #   the eye position and look-at point will follow the front of the car
        if crashed and self.view_mode == "first_person":
            # calculate the current gaze vector
            gaze_vector = self.look_at - self.eye_pos

            ## calculate new look-at point
            gaze_vector = rotate_vector(gaze_vector, pygame.time.get_ticks()//3, "Y")

            # calculate the current look-at point
            new_lookat = self.eye_pos + gaze_vector

        new_eye_pos[0] += lane
        new_eye_pos[2] -= movement
        new_lookat[0] += lane
        new_lookat[2] -= movement

        # return new eye position and look-at point
        return new_eye_pos, new_lookat
    
    def switch_view(self):
        # Switch the current view_mode to the next in the cycle: 
        #   front -> (first_person) -> front ...
        if self.view_mode == "front":
            self.view_mode = "first_person"
            self.eye_pos = np.array([0.0, 10.0, 0.0])
            self.look_at = np.array([0.0, 10.0, -45.0])
            self.view_up = np.array([0.0, 1.0, 0.0])
        elif self.view_mode == "first_person":
            self.view_mode = "front"
            self.eye_pos = np.array([0, 20.0, 50.0])
            self.look_at = np.array([0, 10.0, 0])
            self.view_up = np.array([0.0, 1.0, 0.0])

    def get_view(self):
        return self.eye_pos, self.look_at, self.view_up


class Car:
    def __init__(self, version = "basic"):
        self.version = version 
        self.car_body = [7.0, 5.0, 10.0] # base radius, top radius, height
        self.wheel_radius = 2.0 # wheel radius        
        self.steer = 0.0
        self.lane = 0.0 # lane position
        self.car_speed = 0.0

    # Task 1 and Task 2
    # 1. Create a Basic Scarecrow
    # 2. Rotate its head and nose based on transformation parameters updated by key input
    def draw_body(self):
        """Blue cuboid 10 × 7 × 5 made from a unit cube."""
        glPushMatrix()
        glTranslatef(0, 2, 0)
        glColor3f(0, 1, 0)
        gluSphere(gluNewQuadric(), 3, 32, 32)   # cylinder (r=0.5, length=1)
        glTranslatef(0, -2, 0)
        glColor3f(0.0, 0.0, 1.0)          # blue
        glScalef(*self.car_body)          # length, height, width
        glutSolidCube(1.0)
        glPopMatrix()

    def draw_wheel_core(self, x):
        """Yellow wheel: cylinder (r=2, length=1) with two caps."""
        quadric = gluNewQuadric()
        glTranslatef(0.0, 0.0, 0.5)   # orient cylinder axis along +Z
        glRotatef(self.car_speed, 0.0, 0.0, 1.0)
        glScalef(1, 0.8, 1.2)
        glColor3f(1.0, 1.0, 0.0)          # yellow
        #gluCylinder(quadric, self.wheel_radius, self.wheel_radius, 1.0, 32, 1)
        glutSolidTorus(self.wheel_radius-1, self.wheel_radius, 32, 32)   # cylinder (r=0.5, length=1)

        # far cap
        glPushMatrix()
        glColor3f(1.0, 0.5, 0.0)
        if x < 0:
            glTranslatef(0.0, 0.0, -1.0)
        else:
            glTranslatef(0.0, 0.0, 1.0)
        gluDisk(quadric, 0.0, self.wheel_radius, 32, 1)
        glPopMatrix()

    def place_wheel(self, x, y, z, steer=0):
        """Position wheel so its centre coincides with a body corner."""
        glPushMatrix()
        glTranslatef(x, y, z)
        glRotatef(steer, 0.0, 1.0, 0.0)   # orient cylinder axis along +Z
        glRotatef(90.0, 0.0, 1.0, 0.0)   # orient cylinder axis along +X
        glTranslatef(0.0, 0.0, -0.5)     # centre thickness about the corner
        self.draw_wheel_core(x)
        glPopMatrix()
    
    def turn(self, direction):
        if direction == 'left':
            self.steer += 30
            self.lane -= 10
        if direction == 'right':
            self.steer -= 30
            self.lane += 10

    # ------------ GLUT callbacks ------------
    def drawCar(self, movement=0, crashed=0):
        self.car_speed = movement
        glTranslatef(self.lane, 0.0, -movement)
        if crashed:
            glRotatef(pygame.time.get_ticks()//3, 0.0, 1.0, 0.0)   # rotate around Y axis
        self.draw_body()
        # Body extents (half‑sizes) → ±5 x ±3.5 x ±2.5 around origin
        bx, by, bz = 4.0, -3.5, 5
        self.place_wheel( bx, by,  bz)   # front‑right
        self.place_wheel(-bx, by,  bz)   # front‑left
        self.place_wheel( bx, by, -bz, self.steer)   # rear‑right
        self.place_wheel(-bx, by, -bz, self.steer)   # rear‑left

        glutSwapBuffers()

    def jumpingCar(self, victory):
        glPushMatrix()
        num = np.sin(pygame.time.get_ticks()/1000.0)*2
        if victory: num*=2
        height = abs(num) * 4
        scale = abs(num) * 0.1

        for i in range(1):
            glPushMatrix()
            glTranslatef(0, height+2, 0)
            glColor3f(0, 1, 0)
            gluSphere(gluNewQuadric(), 3, 32, 32)   # cylinder (r=0.5, length=1)
            glPopMatrix()
        glScalef(1, scale+1, 1)
        glTranslatef(0, abs(num), 0)
        glRotatef(num, 0.0, 0.0, 1.0)
        glColor3f(0.0, 0.0, 1.0)          # blue
        glScalef(*self.car_body)          # length, height, width
        glutSolidCube(1.0)
        glPopMatrix()
        # Body extents (half‑sizes) → ±5 x ±3.5 x ±2.5 around origin
        bx, by, bz = 4.0, -3.5, 5
        self.place_wheel( bx, by,  bz)   # front‑right
        self.place_wheel(-bx, by,  bz)   # front‑left
        self.place_wheel( bx, by, -bz, self.steer)   # rear‑right
        self.place_wheel(-bx, by, -bz, self.steer)   # rear‑left

        glutSwapBuffers()


