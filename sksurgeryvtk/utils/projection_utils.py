# -*- coding: utf-8 -*-

"""
Any useful little utilities to do with projecting 3D to 2D.
"""

import cv2
import numpy as np
from numpy.core.umath_tests import inner1d
import sksurgerycore.utilities.validate_matrix as vm

# pylint: disable=no-member


def _validate_input_for_projection(points,
                                   world_to_camera,
                                   camera_matrix,
                                   distortion=None):
    """
    Validation of input, for both project_points and
    project_facing_points.

    :param points: nx3 ndarray representing 3D points, typically in millimetres
    :param world_to_camera: 4x4 ndarray representing world to camera transform
    :param camera_matrix: 3x3 ndarray representing OpenCV camera intrinsics
    :param distortion: 1x4,5 etc. OpenCV distortion parameters
    :raises ValueError, TypeError:
    :return: nx2 ndarray representing 2D points, typically in pixels
    """
    if points is None:
        raise ValueError('points is NULL')
    if not isinstance(points, np.ndarray):
        raise TypeError('points is not an np.ndarray')
    if len(points.shape) != 2:
        raise ValueError("points should have 2 dimensions.")
    if points.shape[1] != 3:
        raise ValueError("points should have 3 columns.")

    if world_to_camera is None:
        raise ValueError('world_to_camera is NULL')
    if not isinstance(world_to_camera, np.ndarray):
        raise TypeError('world_to_camera is not an np.ndarray')
    if len(world_to_camera.shape) != 2:
        raise ValueError("world_to_camera should have 2 dimensions.")
    if world_to_camera.shape[0] != 4:
        raise ValueError("world_to_camera should have 4 rows.")
    if world_to_camera.shape[1] != 4:
        raise ValueError("world_to_camera should have 4 columns.")

    if camera_matrix is None:
        raise ValueError('camera_matrix is NULL')

    vm.validate_camera_matrix(camera_matrix)

    if distortion is not None:
        vm.validate_distortion_coefficients(distortion)


def project_points(points,
                   world_to_camera,
                   camera_matrix,
                   distortion=None
                   ):
    """
    Projects all 3D points to 2D.

    :param points: nx3 ndarray representing 3D points, typically in millimetres
    :param world_to_camera: 4x4 ndarray representing world to camera transform
    :param camera_matrix: 3x3 ndarray representing OpenCV camera intrinsics
    :param distortion: 1x4,5 etc. OpenCV distortion parameters
    :raises ValueError, TypeError:
    :return: nx2 ndarray representing 2D points, typically in pixels
    """

    _validate_input_for_projection(points,
                                   world_to_camera,
                                   camera_matrix,
                                   distortion)

    t_vec = np.zeros((3, 1))
    t_vec[0:3, :] = world_to_camera[0:3, 3:4]
    r_vec, _ = cv2.Rodrigues(world_to_camera[0:3, 0:3])

    projected, _ = cv2.projectPoints(points,
                                     r_vec,
                                     t_vec,
                                     camera_matrix,
                                     distortion
                                     )
    return projected


def project_facing_points(points,
                          normals,
                          world_to_camera,
                          camera_matrix,
                          distortion=None,
                          upper_cos_theta=0
                          ):
    """
    Projects 3D points that face the camera to 2D pixels.

    This assumes:

      Camera direction is a unit vector from the camera, towards focal point.
      Surface Normal is a unit vector pointing out from the surface.

    Vectors are not checked for unit length.

    :param points: nx3 ndarray representing 3D points, typically in millimetres
    :param normals: nx3 ndarray representing unit normals for the same points
    :param world_to_camera: 4x4 ndarray representing world to camera transform
    :param camera_matrix: 3x3 ndarray representing OpenCV camera intrinsics
    :param distortion: 1x4,5 etc. OpenCV distortion parameters
    :param upper_cos_theta: upper limit for cos theta, angle between normal
    and viewing direction, where cos theta is normally -1 to 0.
    :raises ValueError, TypeError:
    :return: projected_facing_points_2d, facing_points_3d
    """
    _validate_input_for_projection(points,
                                   world_to_camera,
                                   camera_matrix,
                                   distortion)

    if normals is None:
        raise ValueError("normals is NULL")
    if not isinstance(normals, np.ndarray):
        raise TypeError('normals is not an np.ndarray')
    if normals.shape != points.shape:
        raise ValueError("normals and points should have the same shape")

    camera_to_world = np.linalg.inv(world_to_camera)
    camera_pose = np.array([[0, 0], [0, 0], [0, 1]])  # Origin and focal point
    transformed = np.matmul(camera_to_world[0:3, 0:3], camera_pose)
    camera_direction = np.array([[transformed[0][1] - transformed[0][0]],
                                 [transformed[1][1] - transformed[1][0]],
                                 [transformed[2][1] - transformed[2][0]]
                                 ]
                                )
    camera_direction_t = camera_direction.transpose()

    facing_points = points[inner1d(normals, camera_direction_t)
                           < upper_cos_theta]

    projected_points = project_points(facing_points,
                                      world_to_camera,
                                      camera_matrix,
                                      distortion
                                      )

    return projected_points, facing_points
