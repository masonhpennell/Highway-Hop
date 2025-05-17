import sys, pygame, time
from pygame.locals import *
from pygame.constants import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

from OBJFileLoader import *
from model import *
from obstacles import *

import numpy as np
from collections import defaultdict

width, height = 1200, 700 
lane_size = 5

class Timer:
    def __init__(self, duration):
        self.duration = duration
        self.start_time = time.time()

    def is_finished(self):
        if self.start_time is None:
            return False
        return (time.time() - self.start_time) >= self.duration

    def remaining_time(self):
        if self.is_finished():
            return 0
        return int(max(0, self.duration - (time.time() - self.start_time)))+1

########################################### OpenGL Program ####################################################
def drawRoad():
    glLineWidth(15.0)
    glBegin(GL_LINES)
    glColor3f(0.7, 0.7, 0.7)
    for i in range(-30, 30, 10):
        glVertex3f(i+lane_size, 0.0, 50)
        glVertex3f(i+lane_size, 0.0, -600)
    glEnd()

def drawGround(victory):
    ground_vertices = [[-500, -12.6, -500],
                       [-500, -12.6, 500],
                       [500, -12.6, 500],
                       [500, -12.6, -500]]

    if victory:
        glColor3f(0, 1, 0)
    else:
        glColor3f(1, 0, 0)
    glBegin(GL_QUADS)
    for vertex in ground_vertices:
        glVertex3fv(vertex)
    glEnd()

def finish(victory):
    screen = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
    message = ""
    if victory:
        message = "You Won!"
    else:
        message = "You Lose! Try to collect more coins next time."

    glEnable(GL_LIGHTING)
    glEnable(GL_COLOR_MATERIAL)
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, width/height, 0.1, 1000.0)

    glMatrixMode(GL_MODELVIEW)
    initmodelMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
    modelMatrix = np.array(initmodelMatrix, copy=True)
    car = Car()
    camera = Camera(False)
    horizontal = 0
    zoom = 0

    glPushMatrix()
    # Light 0 - point light from above, left, front
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 200, 100, 0.0))  # directional light (sunlight)
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (0.5, 0.5, 0.5, 1.0))

    # Light 1 - point light from the left
    glEnable(GL_LIGHT1)
    glLightfv(GL_LIGHT1, GL_POSITION, (-100, 100, 100, 1.0))  # point light
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT1, GL_SPECULAR, (0.5, 0.5, 0.5, 1.0))

    # Light 2 - point light from the right
    glEnable(GL_LIGHT2)
    glLightfv(GL_LIGHT2, GL_POSITION, (100.0, 100.0, 100.0, 1.0))   # point light
    glLightfv(GL_LIGHT2, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT2, GL_SPECULAR, (0.5, 0.5, 0.5, 1.0))
    glPopMatrix()

    while True:
        pygame.display.set_caption(message)
        glPushMatrix()
        glLoadIdentity()
        
        for e in pygame.event.get():
            if e.type == QUIT:
                sys.exit()
            if e.type == MOUSEMOTION:
                pass
            if e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    sys.exit()

        if pygame.key.get_pressed()[K_LEFT]:
            horizontal -= 1
        if pygame.key.get_pressed()[K_RIGHT]:
            horizontal += 1
        if pygame.key.get_pressed()[K_UP]:
            zoom += 1
        if pygame.key.get_pressed()[K_DOWN]:
            zoom -= 1

        glMultMatrixf(modelMatrix)
        modelMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
        
        # draw mesh
        glLoadIdentity()
        
        eye_pos = camera.rotate(horizontal, zoom)

        # Use updated camera parameters to update camera model
        gluLookAt(*eye_pos, 0, 10, 0, 0, 1, 0)
        
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        drawGround(victory)
        car.jumpingCar() # add losing animation

        glPopMatrix()
        pygame.display.flip()
        pygame.time.wait(10)

def main():
    glutInit()

    screen = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)

    glEnable(GL_LIGHTING)
    glEnable(GL_COLOR_MATERIAL)
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, width/height, 0.1, 1000.0)

    glMatrixMode(GL_MODELVIEW)
    initmodelMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
    modelMatrix = np.array(initmodelMatrix, copy=True)

    glPushMatrix()
    glLoadIdentity()
    # Light 0 - point light from above, left, front
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 0, 100, 1.0))  # point light
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (0.5, 0.5, 0.5, 1.0)) # softer white highlight
    glPopMatrix()

    # Movement Variables
    movement    = 0 # initial position
    lane        = 0 # initial lane
    score       = 0 # initial score
    speed       = 0 # initial speed
    finish      = 600 # finish line
    max_speed   = 2
    acceleration= 0.03 
    win         = 5 # number of coins to win

    # Obstacle and Coin Positions
    cone_places = [(np.random.randint(-2, 2)*10, 0, np.random.randint(-finish, 0)) for _ in range(10)]
    coin_places = [(np.random.randint(-2, 2)*10, 5, np.random.randint(-finish, 0)) for _ in range(10)]

    # Create objects
    car = Car()
    cones = Obstacles('traffic', cone_places)
    coins = Obstacles('SimpleGoldCoin', coin_places, True)
    camera = Camera(True, lane, movement) # default view mode is "front"
    timer = Timer(30)
    crashed = False
    countdown = True
    crash_timer = None  # Timer to track crash duration
    
    # main loop
    while True:
        pygame.display.set_caption('Driving Game - Coins: '+str(score)
                                   +' - Time: '+str(timer.remaining_time()))
        bResetModelMatrix = False
        glPushMatrix()
        glLoadIdentity()
        
        for e in pygame.event.get():
            if e.type == QUIT:
                sys.exit()
            if e.type == KEYDOWN:
                if not crashed:
                    # Turn left or right
                    if e.key == K_RIGHT and lane < 20:
                        car.turn('right')
                        lane += 10
                    elif e.key == K_LEFT and lane > -20:
                        car.turn('left')
                        lane -= 10
                # Switch to first-person view
                if e.key == K_SPACE:
                    camera.switch_view()
                elif e.key == K_ESCAPE:
                    sys.exit()

        if crashed and crash_timer is None:
            crash_timer = time.time()  # Start the crash timer
            print("Crashed!")

        if crash_timer is not None:
            if time.time() - crash_timer >= 1:  # Check if 1 second has passed
                crashed = False
                crash_timer = None  # Reset the timer

        # Check for collisions
        crashed = cones.collision(np.array([lane, 0, -movement+4]), lane_size) or crashed
        if coins.collision(np.array([lane, 5, -movement+2]), lane_size):
            score += 1
            print("Coin collected!")
        
        # draw mesh
        glLoadIdentity()
        
        # Update camera parameters based on lane and movement
        new_eye_pos, new_lookat = camera.update_view(lane, movement, crashed)

        # Use updated camera parameters to update camera model
        gluLookAt(new_eye_pos[0], new_eye_pos[1], new_eye_pos[2], 
                  new_lookat[0], new_lookat[1],new_lookat[2],
                  camera.view_up[0], camera.view_up[1], camera.view_up[2])
        
        glClearColor(0, 0, 0.3, 1)
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        drawRoad()
        cones.drawMeshes()
        coins.drawMeshes()
        car.drawCar(movement, crashed)
        # Check if player has won
        if movement < finish and not crashed:
            movement += speed
        elif crashed:
            speed = 0
        elif movement >= finish and score >= win:
            return True
        elif movement >= finish and score < win:
            return False
        if speed < max_speed:
            speed += acceleration

        glPopMatrix()
        pygame.display.flip()
        pygame.time.wait(10)
        # countdown
        if countdown:
            for i in range(3, 0, -1):
                print(f"{i}...")
                time.sleep(1)
            print("Go!")
            countdown = False

if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    print("Use the arrow keys to move the camera.")
    finish(main())
