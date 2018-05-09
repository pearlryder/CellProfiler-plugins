# coding=utf-8

"""
SeedObjects
===========

**SeedObjects** generates *seeds* or *markers* based on an input set of objects.

**SeedObjects** can be run *before* any module that uses seeds (e.g., **Watershed**).
Seeds are generated from the objects in a four step process:

#. Compute the `Euclidean distance transformation`_ of the segmented objects

#. Smooth the transformed image with a Gaussian filter

#. Compute the `local maxima`_

#. Dilate the seeds as specified

This algorithm attempts to locate the centers of objects even if they are under-segmented.

.. Euclidean distance transformation: https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.ndimage.morphology.distance_transform_edt.html
.. local maxima: http://scikit-image.org/docs/dev/api/skimage.feature.html#peak-local-max

|

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES          NO
============ ============ ===============

"""

import numpy
import skimage.morphology
import skimage.segmentation
import scipy.ndimage
import skimage.filters
import skimage.feature
import skimage.util

import cellprofiler.image
import cellprofiler.module
import cellprofiler.setting


class SeedObjects(cellprofiler.module.ObjectProcessing):
    category = "Advanced"

    module_name = "SeedObjects"

    variable_revision_number = 1

    def create_settings(self):
        super(SeedObjects, self).create_settings()

        self.gaussian_sigma = cellprofiler.setting.Float(
            text="Standard deviation for Gaussian kernel",
            value=1.,
            doc="Sigma defines how 'smooth' the Gaussian kernal makes the image. Higher sigma means a smoother image."
        )

        self.min_dist = cellprofiler.setting.Integer(
            text="Minimum distance between seeds",
            value=1,
            minval=0,
            doc="""\
Minimum number of pixels separating peaks in a region of `2 * min_distance + 1 `
(i.e. peaks are separated by at least min_distance). 
To find the maximum number of peaks, set this value to `1`. 
"""
        )

        self.min_intensity = cellprofiler.setting.Float(
            text="Minimum absolute internal distance",
            value=0.,
            minval=0.,
            doc="""\
Minimum absolute intensity threshold for seed generation. Since this threshold is
applied to the distance transformed image, this defines a minimum object
"size". Objects smaller than this size will not contain seeds. 

By default, the absolute threshold is the minimum value of the image.
For distance transformed images, this value is `0` (or the background).
"""
        )

        self.exclude_border = cellprofiler.setting.Integer(
            text="Pixels from border to exclude",
            value=0,
            minval=0,
            doc="Exclude seed generation from within `n` pixels of the image border."
        )

        self.max_seeds = cellprofiler.setting.Integer(
            text="Maximum number of seeds",
            value=-1,
            doc="""\
Maximum number of seeds to generate. Default is no limit. 
When the number of seeds exceeds this number, seeds are chosen 
based on largest internal distance.
"""
        )

        self.structuring_element = cellprofiler.setting.StructuringElement(
            text="Structuring element for seed dilation",
            doc="""\
Structuring element to use for dilating the seeds. 
Volumetric images will require volumetric structuring elements.
"""
        )

    def settings(self):
        __settings__ = super(SeedObjects, self).settings()

        return __settings__ + [
            self.gaussian_sigma,
            self.min_dist,
            self.min_intensity,
            self.exclude_border,
            self.max_seeds,
            self.structuring_element
        ]

    def visible_settings(self):
        __settings__ = super(SeedObjects, self).visible_settings()

        return __settings__ + [
            self.gaussian_sigma,
            self.min_dist,
            self.min_intensity,
            self.exclude_border,
            self.max_seeds,
            self.structuring_element
        ]

    def run(self, workspace):
        x = workspace.object_set.get_objects(self.x_name.value)

        strel_dim = self.structuring_element.value.ndim

        im_dim = x.segmented.ndim

        # Make sure structuring element matches image dimension
        if strel_dim != im_dim:
            raise ValueError("Structuring element does not match object dimensions: "
                             "{} != {}".format(strel_dim, im_dim))

        self.function = lambda labels, sigma, distance_threshold, intensity_threshold, border, max_seeds, s_elem:\
            generate_seeds(labels, sigma, distance_threshold, intensity_threshold, border, max_seeds, s_elem)

        super(SeedObjects, self).run(workspace)


def generate_seeds(labels, gaussian_sigma, distance_threshold, intensity_threshold, border, max_seeds, s_elem):
    # Modify settings to correspond to appropriate library defaults
    if max_seeds == -1:
        max_seeds = numpy.inf

    # Pad the image so the distance transform works as expected
    padded = skimage.util.pad(labels, 1, mode='constant', constant_values=0)

    # Compute the distance transform
    seeds = scipy.ndimage.distance_transform_edt(padded)

    # Remove the pad for the next step
    seeds = skimage.util.crop(seeds, 1)

    # Smooth the image
    seeds = skimage.filters.gaussian(seeds, sigma=gaussian_sigma)

    # Generate local peaks
    seeds = skimage.feature.peak_local_max(seeds,
                                           min_distance=distance_threshold,
                                           threshold_rel=intensity_threshold,
                                           exclude_border=border,
                                           num_peaks=max_seeds,
                                           indices=False)

    # Dilate seeds based on settings
    seeds = skimage.morphology.binary_dilation(seeds, s_elem)

    return seeds


