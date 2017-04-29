# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 14:35:26 2017

@author: carmonda
"""
import sys
from scipy import misc
import numpy as np

# threshold of intensities used in phi calculation
VMAX = 50
# number of iterations -
ITERATIONS = 100


class Vertex(object):
    def __init__(self, name='', y=None, neighs=None, in_msgs=None, observed=True):
        self._name = name
        self._y = y  # original pixel
        if (neighs == None): neighs = set()  # set of neighbour nodes
        if (in_msgs == None): in_msgs = {}  # dictionary mapping neighbours to their messages
        self._neighs = neighs
        self._in_msgs = in_msgs
        # Add is observed field
        self._observed = observed

    def add_neigh(self, vertex):
        self._neighs.add(vertex)

    def rem_neigh(self, vertex):
        self._neighs.remove(vertex)

    def get_belief(self):
        """
        Return the belief according to the last messages
        :return: xi
        """
        belief = np.ones((256))
        for m in self._in_msgs:
            belief *= self._in_msgs[m]

        return np.argmax(belief)

    def get_neighbours(self):
        return self._neighs

    def snd_msg(self, neigh):
        """ Combines messages from all other neighbours
            to propagate a message to the neighbouring Vertex 'neigh'.
            :type neigh: Vertex
        """
        phi_mat = get_phi_mat()

        if self._observed:
            # in case observed generate fixed message
            m = np.zeros((256))
            m += phi_mat[self._y][:]

        elif len(self._in_msgs) == 0:
            # Init case
            m = np.ones((256))
        else:
            # Iterative case

            # calc m'
            m_tag_single_entry = np.zeros((256))
            for neigh_name in self._in_msgs:
                # Do not update xj
                if neigh_name == neigh._name:
                    continue
                m_tag_single_entry += self._in_msgs[neigh_name]

            m_tag = np.dot(phi_mat, m_tag_single_entry).flatten()


            # Normalized - calc m
            m_tag_sum = float(np.sum(m_tag))
            m = m_tag / m_tag_sum

        # send msg to neighbour
        neigh.add_in_msg(m, self._name)

    def __str__(self):
        ret = "Name: " + self._name
        ret += "\nNeighbours:"
        neigh_list = ""
        for n in self._neighs:
            neigh_list += " " + n._name
        ret += neigh_list
        return ret

    def add_in_msg(self, value, key=''):
        """
        Append message to in_msg list
        :param neigh_name:
        :param m:
        :return:
        """
        self._in_msgs[key] = value


class Graph(object):
    def __init__(self, graph_dict=None):
        """ initializes a graph object
            If no dictionary is given, an empty dict will be used
        """
        if graph_dict == None:
            graph_dict = {}
        self._graph_dict = graph_dict

    def vertices(self):
        """ returns the vertices of a graph"""
        return list(self._graph_dict.keys())

    def edges(self):
        """ returns the edges of a graph """
        return self._generate_edges()

    def add_vertex(self, vertex):
        """ If the vertex "vertex" is not in
            self._graph_dict, a key "vertex" with an empty
            list as a value is added to the dictionary.
            Otherwise nothing has to be done.
        """
        if vertex not in self._graph_dict:
            self._graph_dict[vertex] = []

    def add_edge(self, edge):
        """ assumes that edge is of type set, tuple, or list;
            between two vertices can be multiple edges.
        """
        edge = set(edge)
        (v1, v2) = tuple(edge)
        if v1 in self._graph_dict:
            self._graph_dict[v1].append(v2)
        else:
            self._graph_dict[v1] = [v2]
        # if using Vertex class, update data:
        if (type(v1) == Vertex and type(v2) == Vertex):
            v1.add_neigh(v2)
            v2.add_neigh(v1)

    def generate_edges(self):
        """ A static method generating the edges of the
            graph "graph". Edges are represented as sets
            with one or two vertices
        """
        e = []
        for v in self._graph_dict:
            for neigh in self._graph_dict[v]:
                if {neigh, v} not in e:
                    e.append({v, neigh})
        return e

    def __str__(self):
        res = "V: "
        for k in self._graph_dict:
            res += str(k) + " "
        res += "\nE: "
        for edge in self._generate_edges():
            res += str(edge) + " "
        return res


def is_observed(row, col):  # helper function for deciding which pixels are observed
    """
    Returns True/False by whether pixel at (row,col) was observed or not
    """
    x1, x2, y1, y2 = 92, 106, 13, 93  # unobserved rectangle borders for 'pinguin-img.png'

    def in_rect(row, col, x1, x2, y1, y2):
        if (row < x1 or row > x2): return False
        if (col < y1 or col > y2): return False
        return True

    return not (in_rect(row, col, x1, x2, y1, y2))


def build_grid_graph(n, m, img_mat):
    """ Builds an nxm grid graph, with vertex values corresponding to pixel intensities.
    n: num of rows
    m: num of columns
    img_mat = np.ndarray of shape (n,m) of pixel intensities
    
    returns the Graph object corresponding to the grid
    """
    V = []
    g = Graph()
    # add vertices:
    for i in range(n * m):
        row, col = (i // m, i % m)
        v = Vertex(name="v" + str(i), y=img_mat[row][col], observed=is_observed(row, col))
        g.add_vertex(v)
        if (i % m) != 0:  # has left edge
            g.add_edge((v, V[i - 1]))
        if i >= m:  # has up edge
            g.add_edge((v, V[i - m]))
        V += [v]
    return g


def grid2mat(grid, n, m):
    """ convertes grid graph to a np.ndarray
    n: num of rows
    m: num of columns
    
    returns: np.ndarray of shape (n,m)
    :type grid: Graph
    """
    mat = np.zeros((n, m))
    l = grid.vertices()  # list of vertices
    for v in l:
        i = int(v._name[1:])
        row, col = (i // m, i % m)
        mat[row][col] = v.get_belief()
    return mat


# process grid:
def grid_process(graph):
    """
    process the graph - runnnig the algorithm for LBP
    :param graph:
    :return:
    """
    vertices = graph.vertices()

    for iter in range(ITERATIONS):
        print("iteration {0}".format(iter))
        for v in vertices:
            # ask for msgs
            for neigh in v.get_neighbours():
                neigh.snd_msg(v)


def get_phi_mat():
    """
    This function will return the phi function
    :return: matrix of phi
    """
    return phi_mat


if __name__ == '__main__':

    # Begin:
    if len(sys.argv) < 2:
        print 'Please specify output filename'
        exit(0)

    # calc phi_mat
    phi_mat = np.zeros((256, 256))
    for xi in range(256):
        for xj in range(256):
            phi_mat[xi][xj] = np.exp(-1 * min(abs(xi - xj), VMAX))

    # Load image:
    img_path = 'penguin-img.png'
    image = misc.imread(img_path)
    n, m = image.shape
    # we selected the image segment to that all image
    # (but we can take any segment as long as it containing the all unobserbed pixles)
    image_segment = image  # here a segment of the original image should be taken

    # Build grid:
    g = build_grid_graph(image_segment.shape[0], image_segment.shape[1], image_segment)

    # process the grid graph
    grid_process(g)

    # Convert grid to image:
    infered_img = grid2mat(g, image_segment.shape[0], image_segment.shape[1])
    image_final = image  # 2017 - plug the inferred values back to the original image
    #image_final[70:120, 5:100] = infered_img
    image_final = infered_img
    # save result to output file
    outfile_name = sys.argv[1]
    misc.toimage(image_final).save(outfile_name + '.png')
