import numpy
import scipy.ndimage
import skimage.segmentation
import skimage.util

import cellprofiler.measurement
import cellprofiler.module
import cellprofiler.setting
import microscopeimagequality.prediction
import microscopeimagequality.miq

__doc__ = """
<p>This module can collect measurements indicating possible image aberrations,
e.g. blur (poor focus), intensity, saturation (i.e., the percentage
of pixels in the image that are minimal and maximal). Details and guidance for
each of these measures is provided in the settings help.
</p>
"""

C_IMAGE_QUALITY = "ImageQuality"
F_SCORE = "Score"

class MeasureImageQualityGoogle(cellprofiler.module.Module):
    category = "Measurement"

    module_name = "MeasureImageQualityGoogle"

    variable_revision_number = 1

    def create_settings(self):
        self.image_name = cellprofiler.setting.ImageNameSubscriber(
            "Image",
            doc="""
            The name of an image.
            """
        )

    def settings(self):
        return [
            self.image_name
        ]

    #TODO: display matplotlib plot
    def display(self, workspace, figure=None):
        figure.set_subplots((1, 1))
        figure.subplot_table(0, 0,
                             workspace.display_data.statistics)

    def get_categories(self, pipeline, object_name):
        if object_name == cellprofiler.measurement.IMAGE:
            return [
                C_IMAGE_QUALITY
            ]

        return []

    def get_feature_name(self, name):
        image = self.image_name.value

        return C_IMAGE_QUALITY + "_{}_{}".format(name, image)

    def get_measurements(self, pipeline, object_name, category):
        name = self.image_name.value

        if object_name == cellprofiler.measurement.IMAGE and category == C_IMAGE_QUALITY:
            return [
                C_IMAGE_QUALITY + "_" + F_SCORE + "_{}".format(name)
            ]

        return []

    def get_measurement_columns(self, pipeline):
        image = cellprofiler.measurement.IMAGE

        features = [
            self.get_measurement_name(F_SCORE)
        ]

        column_type = cellprofiler.measurement.COLTYPE_INTEGER

        return [(image, feature, column_type) for feature in features]

    def get_measurement_images(self, pipeline, object_name, category, measurement):
        if measurement in self.get_measurements(pipeline, object_name, category):
            return [self.image_name.value]

        return []

    def get_measurement_name(self, name):
        feature = self.get_feature_name(name)

        return feature

    def measure(self, image, workspace):
        """
        get image quality score
        """
        #TODO: check if model downloaded
        microscopeimagequality.miq.download_model()
        m = microscopeimagequality.prediction.ImageQualityClassifier(microscopeimagequality.miq.DEFAULT_MODEL_PATH, 84, 11)
        return m.predict(image)[0]

    def run(self, workspace):
        image_set = workspace.image_set
        image = image_set.get_image(self.image_name.value, must_be_grayscale=True)

        data = image.pixel_data

        measurements = workspace.measurements

        statistics = []

        feature = self.get_feature_name(self.image_name.value)
        value = str(self.measure(data, workspace))

        statistics.append([feature, value])

        measurements.add_image_measurement(self.image_name.value, feature, value)

        workspace.display_data.statistics = statistics

    def volumetric(self):
        return True