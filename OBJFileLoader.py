import os, pygame
from OpenGL.GL import *

def load_texture(image_path):
    surf = pygame.image.load(image_path)
    image = pygame.image.tobytes(surf, 'RGBA', 1)
    width, height = surf.get_rect().size
    texid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA,
                 GL_UNSIGNED_BYTE, image)
    return texid

def MTL(filename):
    contents = {}
    mtl = None
    texture_keys = {'map_Kd', 'map_Bump', 'map_Ks', 'map_Ke', 'map_Ka', 'map_d', 'refl'}

    for line in open(filename, "r"):
        line = line.strip()
        if line.startswith('#') or not line:
            continue
        values = line.split()
        key = values[0]

        if key == 'newmtl':
            mtl = contents[values[1]] = {}
        elif mtl is None:
            raise ValueError("MTL file doesn't start with newmtl statement.")
        elif key in texture_keys:
            tex_filename = ' '.join(values[1:]).replace('\\', '/')
            mtl[key] = tex_filename  # store the path
            tex_path = os.path.join("./resources/textures/", tex_filename)
            try:
                mtl[f'texture_{key}'] = load_texture(tex_path)
            except pygame.error as e:
                print(f"Failed to load texture for {key}: {tex_path} ({e})")
                mtl[f'texture_{key}'] = None
        else:
            # Try to parse as floats, fallback to raw string if fails
            try:
                mtl[key] = list(map(float, values[1:]))
            except ValueError:
                mtl[key] = values[1:] if len(values) > 1 else values[1]
    return contents

class OBJ:
    def __init__(self, filename, swapyz=False):
        self.vertices = []
        self.normals = []
        self.texcoords = []
        self.faces = []

        material = None
        self.mtl = {}

        for line in open(filename, "r"):
            if line.startswith('#'):
                continue
            values = line.split()
            if not values:
                continue
            if values[0] == 'v':
                v = list(map(float, values[1:4]))
                if swapyz:
                    v = (v[0], v[2], v[1])
                self.vertices.append(v)
            elif values[0] == 'vn':
                v = list(map(float, values[1:4]))
                if swapyz:
                    v = (v[0], v[2], v[1])
                self.normals.append(v)
            elif values[0] == 'vt':
                self.texcoords.append(list(map(float, values[1:3])))
            elif values[0] in ('usemtl', 'usemat'):
                material = values[1]
            elif values[0] == 'mtllib':
                mtl_path = os.path.join("./resources/models/", values[1])
                self.mtl = MTL(mtl_path)
            elif values[0] == 'f':
                face = []
                texcoords = []
                norms = []
                for v in values[1:]:
                    w = v.split('/')
                    face.append(int(w[0]))
                    texcoords.append(int(w[1]) if len(w) > 1 and w[1] else 0)
                    norms.append(int(w[2]) if len(w) > 2 and w[2] else 0)
                self.faces.append((face, norms, texcoords, material))

        # Build initial display list
        self.rebuild_gl_list()

    # (Re)complile the OpenGL display list based on current geometry and materials
    def rebuild_gl_list(self):
        if hasattr(self, 'gl_list'):
            glDeleteLists(self.gl_list, 1)

        self.gl_list = glGenLists(1)
        glNewList(self.gl_list, GL_COMPILE)
        glEnable(GL_TEXTURE_2D)
        glFrontFace(GL_CCW)

        for face in self.faces:
            vertices, normals, texture_coords, material = face
            mtl = self.mtl.get(material, {})

            tex_id = mtl.get('texture_map_Kd')
            if tex_id:
                glBindTexture(GL_TEXTURE_2D, tex_id)
                glColor3f(1.0, 1.0, 1.0)
            else:
                kd = mtl.get('Kd', [1.0, 1.0, 1.0])
                glColor3f(*kd)

            glBegin(GL_POLYGON)
            for i in range(len(vertices)):
                if normals[i] > 0:
                    glNormal3fv(self.normals[normals[i] - 1])
                if texture_coords[i] > 0:
                    glTexCoord2fv(self.texcoords[texture_coords[i] - 1])
                glVertex3fv(self.vertices[vertices[i] - 1])
            glEnd()

        glDisable(GL_TEXTURE_2D)
        glEndList()    

    # Calculate the min, max values of each x, y, z coordinates of the input mesh
    #   Also, returns the center position (x, y, z), 
    #       and radius (i.e., max value of x, y, z ranges)
    def cal_minMax(self):
        if not self.vertices:
            return None, None, None  # or raise an Exception if preferred

        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]

        min_coords = (min(xs), min(ys), min(zs))
        max_coords = (max(xs), max(ys), max(zs))

        return min_coords, max_coords