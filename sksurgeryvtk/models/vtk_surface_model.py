# -*- coding: utf-8 -*-

"""
VTK pipeline to represent a surface model via a vtkPolyData.
"""

import os
import numpy as np
import vtk
from vtk.util import numpy_support
import sksurgerycore.utilities.validate_file as vf
import sksurgeryvtk.models.vtk_base_model as vbm
import sksurgeryvtk.utils.matrix_utils as mu

# pylint: disable=too-many-instance-attributes


class VTKSurfaceModel(vbm.VTKBaseModel):
    """
    Class to represent a VTK surface model. Normally
    read from a file, but could be created on the fly.
    """
    def __init__(self, filename, colour, visibility=True, opacity=1.0,
                 pickable=True):
        """
        Creates a new surface model.

        :param filename: if None a default, empty, vtkPolyData is created.
        :param colour: (R,G,B) where each are floats [0-1]
        :param visibility: boolean, True|False
        :param opacity: float [0,1]
        :param pickable: boolean, True|False
        """
        super(VTKSurfaceModel, self).__init__(colour, visibility, opacity,
                                              pickable)

        self.source_file = None
        self.reader = None
        self.source = None
        self.texture_file = None
        self.texture_name = None
        self.texture_reader = None
        self.texture = None

        # Works like FactoryMethod. Could be refactored elsewhere.
        if filename is not None:

            vf.validate_is_file(filename)

            if filename.endswith('.vtk'):
                self.reader = vtk.vtkPolyDataReader()

            elif filename.endswith('.stl'):
                self.reader = vtk.vtkSTLReader()

            elif filename.endswith('.ply'):
                self.reader = vtk.vtkPLYReader()

            elif filename.endswith('.vtp'):
                self.reader = vtk.vtkXMLPolyDataReader()
            else:
                raise ValueError(
                    'File type not supported for model loading: {}'.format(
                        filename))

            self.reader.SetFileName(filename)
            self.reader.Update()
            self.source = self.reader.GetOutput()

            self.source_file = filename
            self.name = os.path.basename(self.source_file)
        else:
            # Creates a new empty vtkPolyData, that the client
            # can dynamically fill with new data.
            self.source = vtk.vtkPolyData()
            self.name = ""

        # Only create normals if there are none on input
        self.normals = None
        if self.source.GetPointData().GetNormals() is None:
            self.normals = vtk.vtkPolyDataNormals()
            self.normals.SetInputData(self.source)
            self.normals.SetAutoOrientNormals(True)
            self.normals.SetFlipNormals(False)
        self.transform = vtk.vtkTransform()
        self.transform.Identity()
        self.transform_filter = vtk.vtkTransformPolyDataFilter()
        if self.normals is None:
            self.transform_filter.SetInputData(self.source)
        else:
            self.transform_filter.SetInputConnection(
                self.normals.GetOutputPort())
        self.transform_filter.SetTransform(self.transform)
        self.mapper = vtk.vtkPolyDataMapper()
        self.mapper.SetInputConnection(self.transform_filter.GetOutputPort())
        self.mapper.Update()
        self.actor.SetMapper(self.mapper)

    def set_model_transform(self, matrix):
        """
        Sets the model to world transform onto a vtkPolyDataFilter.
        This enables all the points and point data to be transformed
        according to a vtkMatrix4x4 similarity transform.
        :param matrix: vtkMatrix4x4
        """
        mu.validate_vtk_matrix_4x4(matrix)
        self.transform.SetMatrix(matrix)
        self.transform_filter.SetTransform(self.transform)

    def get_model_transform(self):
        """
        Gets the model to world transform.
        :return: vtkMatrix4x4
        """
        return self.transform.GetMatrix()

    def get_number_of_points(self):
        """
        Returns the number of points in the vtkPoylData.
        :return: unsigned int
        """
        self.transform_filter.Update()
        number_of_points = self.transform_filter.GetOutput().GetNumberOfPoints()
        return number_of_points

    def get_points_as_numpy(self):
        """
        Returns the vtkPolyData points as a numpy array.
        :return: nx3 numpy ndarray
        """
        self.transform_filter.Update()
        vtk_points = self.transform_filter.GetOutput().GetPoints()
        as_numpy = numpy_support.vtk_to_numpy(vtk_points.GetData())
        return as_numpy

    def get_normals_as_numpy(self):
        """
         Returns the vtkPolyData point normals as a numpy array.
        :return: nx3 numpy ndarray
        """
        self.transform_filter.Update()
        vtk_normals = self.transform_filter \
            .GetOutput().GetPointData().GetNormals()
        as_numpy = numpy_support.vtk_to_numpy(vtk_normals)
        return as_numpy

    def set_texture(self, filename):
        """
        Sets an image from a file as a texture for the model.
        :param filename:
        :return:
        """
        # Read the texture image from a file.
        # Currently supports png and jpeg formats.
        if filename is not None:

            vf.validate_is_file(filename)

            if filename.endswith('.png'):
                self.texture_reader = vtk.vtkPNGReader()

            elif np.logical_or(filename.endswith('.jpeg'),
                               filename.endswith('.jpg')):
                self.texture_reader = vtk.vtkJPEGReader()

            else:
                raise ValueError(
                    'File type not supported for texture loading: {}'.format(
                        filename))

        else:
            # Unset texture when the function is called with None.
            self.texture_reader = None
            self.texture_file = None
            self.texture_name = None
            self.texture = None
            self.actor.SetTexture(None)
            return

        self.texture_reader.SetFileName(filename)
        self.texture_file = filename
        self.texture_name = os.path.basename(self.texture_file)

        # Create texture object.
        self.texture = vtk.vtkTexture()
        if vtk.VTK_MAJOR_VERSION <= 5:
            self.texture.SetInput(self.texture_reader.GetOutput())
        else:
            self.texture.SetInputConnection(self.texture_reader.GetOutputPort())

        # Set the texture
        self.actor.SetTexture(self.texture)
